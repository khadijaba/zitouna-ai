"""Model loading and inference for M1. This is the file the module owner edits.

Real model (produced by notebooks/m1_disease/train_m1.ipynb, exported into models/m1/):

- model.pt        TorchScript tracé, sortie = logits (avant softmax)
- classes.json    liste des classes (3 : healthy, peacock_spot, aculus_olearius)
- calibration.json  {"temperature": T} — temperature scaling apprise sur le jeu de validation
- model_full.pt   state_dict complet (optionnel) — sert au Grad-CAM en production
- metadata.json   métriques, seed, versions (information)

Chaîne d'inférence (identique au notebook et à evaluate_field.py) :
image → RGB → resize 256 → center crop 224 → normalisation ImageNet → logits TorchScript
→ softmax(logits / T) → argmax. Si la confiance calibrée maximale est < 0.70, aucun diagnostic
n'est donné : le champ advice contient le message « photo peu claire » et lowConfidence = true.

Tant que models/m1/model.pt n'existe pas (ou si torch n'est pas installé), le service répond
en mode mock (mock=True), comme avant — le backend et l'app continuent de fonctionner.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.schemas import DiseaseResponse

logger = logging.getLogger(__name__)

# Relative to the service folder when run locally; Docker sets MODEL_DIR=/models/m1.
MODEL_DIR = Path(os.getenv("MODEL_DIR", "../../models/m1"))
MODEL_FILE = MODEL_DIR / "model.pt"
MODEL_VERSION = os.getenv("MODEL_VERSION", "dev")
TREATMENTS_FILE = Path(__file__).resolve().parent / "treatments.json"
LOW_CONFIDENCE_THRESHOLD = 0.70
# Grad-CAM en production : activé par défaut, désactivable (M1_HEATMAP=0) si trop lent.
HEATMAP_ENABLED = os.getenv("M1_HEATMAP", "1") == "1"

# torch/torchvision sont volumineux : import gardé pour que le mode mock fonctionne sans eux.
try:
    import torch
    from torchvision.models import mobilenet_v3_large

    try:
        from torchvision.transforms import v2 as tft  # torchvision >= 0.15 : ToImage/ToDtype y vivent
    except ImportError:  # pragma: no cover - très anciennes versions
        from torchvision import transforms as tft
except ImportError:  # pragma: no cover - environnement sans torch
    torch = None

CLASSES = ["healthy", "peacock_spot", "aculus_olearius", "olive_knot"]
LABELS_FR = {
    "healthy": "Feuille saine",
    "peacock_spot": "Œil de paon",
    "aculus_olearius": "Aculus olearius (acarien)",
    "olive_knot": "Tuberculose de l'olivier",
}


class InvalidImageError(ValueError):
    pass


@dataclass
class LoadedModel:
    """Tout ce qu'il faut pour une inférence réelle (voir load())."""

    scripted: object  # torch.jit.ScriptModule — logits en sortie
    classes: list[str]
    temperature: float
    full: object | None = None  # modèle eager reconstruit, pour le Grad-CAM


def load() -> LoadedModel | None:
    """Return the trained model, or None to run in mock mode."""
    if torch is None:
        logger.warning("torch non installé : mode mock")
        return None
    if not MODEL_FILE.exists():
        return None
    try:
        scripted = torch.jit.load(str(MODEL_FILE), map_location="cpu")
        scripted.eval()
        classes = CLASSES
        if (MODEL_DIR / "classes.json").exists():
            classes = json.loads((MODEL_DIR / "classes.json").read_text(encoding="utf-8"))
        temperature = 1.0
        if (MODEL_DIR / "calibration.json").exists():
            temperature = json.loads((MODEL_DIR / "calibration.json").read_text(encoding="utf-8")).get(
                "temperature", 1.0
            )
        full = _load_full_model(classes)
        logger.info("Modèle M1 chargé : %d classes, T=%s, gradcam=%s", len(classes), temperature, full is not None)
        return LoadedModel(scripted=scripted, classes=classes, temperature=temperature, full=full)
    except Exception:
        logger.exception("Échec du chargement du modèle M1 : passage en mode mock")
        return None


def _load_full_model(classes: list[str]):
    """Reconstruit le modèle eager depuis model_full.pt pour le Grad-CAM (optionnel)."""
    full_path = MODEL_DIR / "model_full.pt"
    if not HEATMAP_ENABLED or not full_path.exists():
        return None
    try:
        model = mobilenet_v3_large(weights=None)
        model.classifier[3] = torch.nn.Linear(model.classifier[3].in_features, len(classes))
        # weights_only: the file holds a state_dict, so refuse pickled objects (no code execution from a tampered file).
        model.load_state_dict(torch.load(full_path, map_location="cpu", weights_only=True))
        model.eval()
        return model
    except Exception:
        logger.exception("model_full.pt non exploitable : Grad-CAM désactivé")
        return None


def predict(model: LoadedModel | None, image_bytes: bytes) -> DiseaseResponse:
    image = _open_image(image_bytes)
    if model is None or torch is None:
        return _mock(image_bytes)

    # Prétraitement STRICTEMENT identique au notebook (m1_common.build_transforms(train=False))
    # et à evaluate_field.py : resize 256 -> center crop 224 -> [0,1] -> normalisation ImageNet.
    mean, std = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
    if hasattr(tft, "ToImage"):  # API v2 (torchvision >= 0.15)
        transform = tft.Compose(
            [
                tft.ToImage(),
                tft.Resize(256, antialias=True),
                tft.CenterCrop(224),
                tft.ToDtype(torch.float32, scale=True),
                tft.Normalize(mean, std),
            ]
        )
    else:  # API v1 équivalente (mêmes valeurs)
        transform = tft.Compose([tft.Resize(256), tft.CenterCrop(224), tft.ToTensor(), tft.Normalize(mean, std)])
    tensor = transform(image).unsqueeze(0)

    with torch.no_grad():
        logits = model.scripted(tensor)
    probabilities = torch.softmax(logits / model.temperature, dim=1)[0]
    return _build(
        probabilities={c: float(probabilities[i]) for i, c in enumerate(model.classes)},
        mock=False,
        heatmap=_heatmap(model, tensor),
    )


def _heatmap(model: LoadedModel, tensor) -> str | None:
    """Grad-CAM sur la dernière couche de convolution → PNG en base64 (ou None)."""
    if model.full is None:
        return None
    try:
        target_layer = model.full.features[-1]
        storage: dict[str, torch.Tensor] = {}

        def _keep_activation(_module, _inputs, output):
            output.retain_grad()  # gradient d'une couche intermédiaire (sinon purgé par autograd)
            storage["activation"] = output

        handle = target_layer.register_forward_hook(_keep_activation)
        inp = tensor.detach().clone().requires_grad_(True)
        logits = model.full(inp)
        index = int(logits.argmax())
        model.full.zero_grad()
        logits[0, index].backward()
        activation = storage["activation"]
        weights = activation.grad.mean(dim=(2, 3), keepdim=True)
        cam = torch.relu((weights * activation).sum(dim=1))[0]
        cam = cam / (cam.max() + 1e-8)
        handle.remove()
        model.full.zero_grad()
        return _overlay_base64(inp, cam)
    except Exception:
        logger.exception("Grad-CAM a échoué : réponse sans carte de chaleur")
        return None


def _jet(value: float) -> tuple[float, float, float]:
    """Approximation de la colormap « jet » : bleu → cyan → vert → jaune → rouge."""
    four = 4.0 * value
    clamp = lambda v: max(0.0, min(1.0, v))  # noqa: E731 — plus lisible ainsi
    return (
        clamp(min(four - 1.5, -four + 4.5)),
        clamp(min(four - 0.5, -four + 3.5)),
        clamp(min(four + 0.5, -four + 2.5)),
    )


def _overlay_base64(tensor, cam) -> str:
    """Superpose la carte de chaleur à la photo (dé-normalisée), renvoie du PNG base64 — sans matplotlib."""
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    image = (tensor[0].detach() * std + mean).clamp(0, 1).permute(1, 2, 0).mul(255).byte().numpy()
    leaf = Image.fromarray(image)
    gray = Image.fromarray(cam.mul(255).byte().numpy(), mode="L").resize(leaf.size, Image.BILINEAR)
    lut_r, lut_g, lut_b = [], [], []
    for i in range(256):
        r, g, b = _jet(i / 255.0)
        lut_r.append(int(r * 255))
        lut_g.append(int(g * 255))
        lut_b.append(int(b * 255))
    colored = Image.merge("RGB", (gray.point(lut_r), gray.point(lut_g), gray.point(lut_b)))
    buffer = io.BytesIO()
    Image.blend(leaf, colored, alpha=0.45).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _load_treatments() -> dict:
    try:
        return json.loads(TREATMENTS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("treatments.json illisible : conseils intégrés de secours")
        retake = (
            "Photo peu claire, reprenez-la : une seule feuille bien à plat, à environ 20 cm, de préférence au soleil."
        )
        return {
            "low_confidence": {"advice": retake},
            "classes": {
                c: {
                    "labelFr": LABELS_FR[c],
                    "advice": "Conseil indisponible pour le moment.",
                    "warning": "À valider par un agronome (INRAT / ONH).",
                    "source": "À valider par un agronome (INRAT / ONH).",
                }
                for c in CLASSES
            },
        }


TREATMENTS = _load_treatments()


def _build(probabilities: dict[str, float], mock: bool, heatmap: str | None = None) -> DiseaseResponse:
    label = max(probabilities, key=probabilities.get)
    confidence = probabilities[label]
    low_confidence = not mock and confidence < LOW_CONFIDENCE_THRESHOLD
    entry = TREATMENTS["classes"].get(label, {})
    if low_confidence:
        # Pas de diagnostic : le message de reprise de photo voyage dans « advice »,
        # champ prévu par le contrat et affiché tel quel par le frontend.
        advice = TREATMENTS["low_confidence"]["advice"]
    else:
        advice = entry.get("advice", "Aucun conseil disponible.")
    return DiseaseResponse(
        label=label,
        label_fr=entry.get("labelFr", LABELS_FR.get(label, label)),
        confidence=round(confidence, 4),
        probabilities={k: round(v, 4) for k, v in probabilities.items()},
        advice=advice,
        heatmap_base64=heatmap,
        model_version="mock" if mock else MODEL_VERSION,
        mock=mock,
        low_confidence=low_confidence,
    )


def _mock(image_bytes: bytes) -> DiseaseResponse:
    # Deterministic: the same photo always gives the same fake answer.
    seed = hashlib.sha256(image_bytes).digest()
    winner = CLASSES[seed[0] % len(CLASSES)]
    rest = (1 - 0.82) / (len(CLASSES) - 1)
    response = _build({c: 0.82 if c == winner else rest for c in CLASSES}, mock=True)
    return response


def _open_image(image_bytes: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        return image.convert("RGB")
    except (UnidentifiedImageError, OSError) as e:
        raise InvalidImageError("The uploaded file is not a readable image") from e
