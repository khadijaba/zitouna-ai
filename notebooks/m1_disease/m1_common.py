"""M1 · Bibliothèque commune au notebook d'entraînement et à evaluate_field.py.

Contient : seeds, augmentations « photo terrain », datasets, modèles (baseline CNN +
MobileNetV3), boucle d'entraînement, métriques, Grad-CAM, calibration par temperature
scaling, et exports (TorchScript / ONNX / TFLite).

Importable dans le notebook (Colab : le dossier notebooks/m1_disease est sur Drive,
le notebook ajoute son propre dossier à sys.path) et en script local.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision.models import MobileNet_V3_Large_Weights, mobilenet_v3_large

# ToImage/ToDtype vivent dans torchvision.transforms.v2 (>= 0.15), pas dans le namespace
# de base : on importe v2 en priorité, avec repli sur l'API v1 pour les vieilles versions.
try:
    from torchvision.transforms import v2 as T
except ImportError:  # pragma: no cover - torchvision < 0.15
    from torchvision import transforms as T

# --- Constantes partagées -----------------------------------------------------

SEED = 42
IMG_SIZE = 224
# Classes du contrat M1 réellement présentes dans le dataset Uğuz & Uysal (3 classes).
CLASSES = ["healthy", "peacock_spot", "aculus_olearius"]
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
LOW_CONFIDENCE_THRESHOLD = 0.70
LOW_CONFIDENCE_ADVICE_FR = (
    "Photo peu claire : la feuille est floue, trop petite ou mal éclairée. "
    "Reprenez la photo : une seule feuille bien à plat, à environ 20 cm, au soleil de préférence."
)


def set_seed(seed: int = SEED) -> None:
    """Reproductibilité totale : random, numpy, torch, CUDA (y compris cudnn déterministe)."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


# --- Données -------------------------------------------------------------------

def build_transforms(train: bool, img_size: int = IMG_SIZE) -> T.Compose:
    """Transformes identiques en entraînement et en inférence pour le resize/crop/normalisation.

    Train : augmentations fortes simulant une photo prise au téléphone dans un verger —
    luminosité/contraste/teinte, flou, rotation, recadrage aléatoire, miroir, découpes
    aléatoires (fonds, ombres, doigts devant l'objectif).
    Val/test (et API) : resize 256 -> center crop 224 -> normalisation ImageNet.

    Compatible avec toutes les versions de torchvision : API v2 (ToImage/ToDtype, >= 0.15)
    ou API v1 (ToTensor) selon ce qui est disponible.
    """
    if hasattr(T, "ToImage"):  # torchvision >= 0.15 : API v2
        normalize = T.Normalize(IMAGENET_MEAN, IMAGENET_STD)
        if not train:
            return T.Compose([
                T.ToImage(),
                T.Resize(256, antialias=True),
                T.CenterCrop(img_size),
                T.ToDtype(torch.float32, scale=True),
                normalize,
            ])
        return T.Compose([
            T.ToImage(),
            T.RandomResizedCrop(img_size, scale=(0.6, 1.0), antialias=True),   # recadrage aléatoire
            T.RandomRotation(30),                                              # téléphone rarement droit
            T.RandomHorizontalFlip(),
            T.ColorJitter(brightness=0.35, contrast=0.35, saturation=0.25, hue=0.04),  # lumière du champ
            T.RandomApply([T.GaussianBlur(kernel_size=5, sigma=(0.1, 2.0))], p=0.25),  # flou/mise au point
            T.ToDtype(torch.float32, scale=True),
            normalize,
            T.RandomErasing(p=0.25, scale=(0.02, 0.12)),  # fonds, ombres, doigts devant l'objectif
        ])
    # torchvision < 0.15 : API v1 équivalente (mêmes paramètres)
    normalize = T.Normalize(IMAGENET_MEAN, IMAGENET_STD)
    if not train:
        return T.Compose([T.Resize(256), T.CenterCrop(img_size), T.ToTensor(), normalize])
    return T.Compose([
        T.RandomResizedCrop(img_size, scale=(0.6, 1.0)),
        T.RandomRotation(30),
        T.RandomHorizontalFlip(),
        T.ColorJitter(brightness=0.35, contrast=0.35, saturation=0.25, hue=0.04),
        T.RandomApply([T.GaussianBlur(kernel_size=5, sigma=(0.1, 2.0))], p=0.25),
        T.ToTensor(),
        normalize,
        T.RandomErasing(p=0.25, scale=(0.02, 0.12)),
    ])


class LeafDataset(Dataset):
    """Dataset ImageFolder minimal (train_dir/<classe>/*.jpg), classes triées = CLASSES."""

    def __init__(self, root: str | Path, train: bool):
        self.root = Path(root)
        self.class_to_idx = {c: i for i, c in enumerate(CLASSES)}
        self.samples: list[tuple[Path, int]] = []
        for class_name, idx in self.class_to_idx.items():
            folder = self.root / class_name
            if not folder.is_dir():
                raise FileNotFoundError(f"dossier de classe manquant : {folder}")
            self.samples += [(p, idx) for p in sorted(folder.glob("*")) if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}]
        if not self.samples:
            raise FileNotFoundError(f"aucune image dans {self.root}")
        self.transform = build_transforms(train)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int):
        path, label = self.samples[index]
        image = Image.open(path).convert("RGB")
        return self.transform(image), label

    def count_per_class(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for _, label in self.samples:
            counts[CLASSES[label]] += 1
        return dict(counts)


def make_loaders(data_dir: str | Path, batch_size: int = 32, num_workers: int = 2) -> tuple[DataLoader, DataLoader, DataLoader]:
    data_dir = Path(data_dir)
    train_ds = LeafDataset(data_dir / "train", train=True)
    val_ds = LeafDataset(data_dir / "val", train=False)
    test_ds = LeafDataset(data_dir / "test", train=False)
    common = dict(num_workers=num_workers, pin_memory=torch.cuda.is_available())
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=True, **common)
    val_dl = DataLoader(val_ds, batch_size=batch_size, **common)
    test_dl = DataLoader(test_ds, batch_size=batch_size, **common)
    return train_dl, val_dl, test_dl


def class_weights_from(train_ds: LeafDataset) -> torch.Tensor:
    """Poids de classe (inverse de la fréquence) pour compenser le déséquilibre."""
    counts = torch.zeros(len(CLASSES))
    for _, label in train_ds.samples:
        counts[label] += 1
    weights = counts.sum() / (len(CLASSES) * counts.clamp(min=1))
    return weights


# --- Modèles -------------------------------------------------------------------

class SmallCNN(nn.Module):
    """Baseline volontairement simple : 3 blocs conv + pooling, ~230k paramètres."""

    def __init__(self, num_classes: int = len(CLASSES)):
        super().__init__()
        layers = []
        for in_ch, out_ch in [(3, 32), (32, 64), (64, 128)]:
            layers += [nn.Conv2d(in_ch, out_ch, 3, padding=1), nn.BatchNorm2d(out_ch),
                       nn.ReLU(inplace=True), nn.MaxPool2d(2)]
        self.features = nn.Sequential(*layers)
        self.head = nn.Sequential(nn.AdaptiveAvgPool2d(1), nn.Flatten(),
                                  nn.Linear(128, num_classes))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.features(x))


def build_mobilenet(num_classes: int = len(CLASSES), pretrained: bool = True) -> nn.Module:
    """MobileNetV3-Large : transfer learning ImageNet, tête remplacée par notre classifieur."""
    weights = MobileNet_V3_Large_Weights.IMAGENET1K_V2 if pretrained else None
    model = mobilenet_v3_large(weights=weights)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)
    return model


def set_backbone_frozen(model: nn.Module, frozen: bool) -> None:
    """Gèle (phase 1) ou dégèle (phase 2) tout sauf la tête classifier."""
    for name, param in model.named_parameters():
        param.requires_grad = frozen is False or name.startswith("classifier")


# --- Entraînement ----------------------------------------------------------------

def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    """Renvoie (probas, labels) sur tout le loader, model.eval() sans gradient."""
    model.eval()
    all_probs, all_labels = [], []
    with torch.no_grad():
        for images, labels in loader:
            probs = torch.softmax(model(images.to(device)), dim=1)
            all_probs.append(probs.cpu())
            all_labels.append(labels)
    return torch.cat(all_probs), torch.cat(all_labels)


def train_model(model: nn.Module, train_dl: DataLoader, val_dl: DataLoader, *,
                epochs: int, lr: float, weight_decay: float = 1e-4,
                class_weights: torch.Tensor | None = None, patience: int = 5,
                label_smoothing: float = 0.05, device: torch.device | None = None) -> tuple[nn.Module, dict]:
    """Boucle générique : AdamW + cosine, loss pondérée + label smoothing,
    suivi du meilleur F1 macro sur val (early stopping). Renvoie (meilleur modèle, historique)."""
    device = device or get_device()
    model.to(device)
    weights = class_weights.to(device) if class_weights is not None else None
    criterion = nn.CrossEntropyLoss(weight=weights, label_smoothing=label_smoothing)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    use_amp = device.type == "cuda"
    # torch < 2.3 expose GradScaler sous torch.cuda.amp ; les versions récentes sous torch.amp.
    scaler_factory = getattr(torch.amp, "GradScaler", None) or torch.cuda.amp.GradScaler
    scaler = scaler_factory(enabled=use_amp)

    best_f1, best_state, history = -1.0, None, {"train_loss": [], "val_loss": [], "val_f1_macro": []}
    epochs_without_improvement = 0
    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        for images, labels in train_dl:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast(device_type="cuda", enabled=use_amp):
                loss = criterion(model(images), labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            running_loss += loss.item() * images.size(0)
        scheduler.step()

        val_probs, val_labels = evaluate(model, val_dl, device)
        val_loss = nn.functional.cross_entropy(val_probs.clamp(min=1e-9).log(), val_labels).item()
        f1 = macro_f1(val_probs.argmax(dim=1), val_labels)
        history["train_loss"].append(running_loss / len(train_dl.dataset))
        history["val_loss"].append(val_loss)
        history["val_f1_macro"].append(f1)
        marker = ""
        if f1 > best_f1:
            best_f1, best_state = f1, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            epochs_without_improvement = 0
            marker = "  <- meilleur"
        else:
            epochs_without_improvement += 1
        print(f"epoch {epoch:2d}/{epochs}  train_loss={history['train_loss'][-1]:.4f}  "
              f"val_loss={val_loss:.4f}  val_f1_macro={f1:.4f}{marker}")
        if epochs_without_improvement >= patience:
            print(f"early stopping (pas d'amélioration depuis {patience} epochs)")
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    return model, history


def macro_f1(preds: torch.Tensor, labels: torch.Tensor, num_classes: int = len(CLASSES)) -> float:
    """F1 macro calculé à la main (pas de dépendance sklearn dans les services)."""
    preds, labels = preds.cpu(), labels.cpu()
    f1s = []
    for c in range(num_classes):
        tp = ((preds == c) & (labels == c)).sum().item()
        fp = ((preds == c) & (labels != c)).sum().item()
        fn = ((preds != c) & (labels == c)).sum().item()
        f1s.append(2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0)
    return float(np.mean(f1s))


def classification_report_dict(probs: torch.Tensor, labels: torch.Tensor, class_names: list[str]) -> dict:
    """Accuracy + F1 par classe + macro, sous forme de dictionnaire affichable."""
    preds = probs.argmax(dim=1)
    report = {"accuracy": (preds == labels).float().mean().item()}
    for c, name in enumerate(class_names):
        tp = ((preds == c) & (labels == c)).sum().item()
        fp = ((preds == c) & (labels != c)).sum().item()
        fn = ((preds != c) & (labels == c)).sum().item()
        report[f"f1_{name}"] = round(2 * tp / (2 * tp + fp + fn), 4) if (2 * tp + fp + fn) else 0.0
    report["f1_macro"] = macro_f1(preds, labels, len(class_names))
    return report


def collect_logits(model: nn.Module, loader: DataLoader, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    """Logits bruts (avant softmax) et labels — nécessaire pour la calibration."""
    model.eval()
    logits_list, labels_list = [], []
    with torch.no_grad():
        for images, labels in loader:
            logits_list.append(model(images.to(device)).cpu())
            labels_list.append(labels)
    return torch.cat(logits_list), torch.cat(labels_list)


def confusion_matrix(preds: torch.Tensor, labels: torch.Tensor, num_classes: int = len(CLASSES)) -> np.ndarray:
    """Matrice de confusion : lignes = classe réelle, colonnes = classe prédite."""
    matrix = np.zeros((num_classes, num_classes), dtype=int)
    for true, pred in zip(labels.tolist(), preds.tolist()):
        matrix[true, pred] += 1
    return matrix


def plot_confusion(preds: torch.Tensor, labels: torch.Tensor, class_names: list[str],
                   path: str | Path, title: str) -> None:
    """Matrice de confusion sauvegardée en PNG (annotée, normalisée par ligne)."""
    import matplotlib.pyplot as plt

    matrix = confusion_matrix(preds, labels, len(class_names))
    row_sums = matrix.sum(axis=1, keepdims=True).clip(min=1)
    normalized = matrix / row_sums
    fig, axis = plt.subplots(figsize=(6, 5))
    image = axis.imshow(normalized, cmap="Blues", vmin=0, vmax=1)
    axis.set_xticks(range(len(class_names)), class_names, rotation=30, ha="right")
    axis.set_yticks(range(len(class_names)), class_names)
    axis.set_xlabel("Prédiction")
    axis.set_ylabel("Réalité")
    axis.set_title(title)
    for i in range(len(class_names)):
        for j in range(len(class_names)):
            axis.text(j, i, f"{matrix[i, j]}\n({normalized[i, j]:.0%})", ha="center", va="center",
                      color="white" if normalized[i, j] > 0.5 else "black", fontsize=9)
    fig.colorbar(image, fraction=0.046)
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.show()


# --- Grad-CAM --------------------------------------------------------------------

class GradCAM:
    """Grad-CAM sur la dernière couche de convolution (features[-1] de MobileNetV3, 7x7).

    Usage : cam, index = gradcam(image_batch) ; overlay = gradcam.overlay(pil_image, cam).
    """

    def __init__(self, model: nn.Module, target_layer: nn.Module | None = None):
        self.model = model.eval()
        self.target_layer = target_layer if target_layer is not None else model.features[-1]
        self._activations: torch.Tensor | None = None
        self._gradients: torch.Tensor | None = None
        # Handles conservés : remove() obligatoire avant un export torch.jit/ONNX
        # (trace refuse les modules portant des hooks — voir export_all).
        self._handles = [
            self.target_layer.register_forward_hook(self._save_activation),
            self.target_layer.register_full_backward_hook(self._save_gradient),
        ]

    def remove(self) -> None:
        """Détache les hooks : à appeler quand on n'utilise plus le Grad-CAM."""
        for handle in self._handles:
            handle.remove()
        self._handles.clear()

    def _save_activation(self, _module, _inputs, output):
        self._activations = output.detach()

    def _save_gradient(self, _module, grad_input, _grad_output):
        self._gradients = _grad_output[0].detach()

    def __call__(self, image_batch: torch.Tensor, class_index: int | None = None) -> tuple[torch.Tensor, int]:
        logits = self.model(image_batch)
        index = int(logits.argmax(dim=1).item()) if class_index is None else class_index
        self.model.zero_grad(set_to_none=True)
        logits[0, index].backward()
        weights = self._gradients.mean(dim=(2, 3), keepdim=True)          # importance de chaque canal
        cam = torch.relu((weights * self._activations).sum(dim=1))[0]     # (7, 7)
        cam = cam / (cam.max() + 1e-8)                                    # normalisation [0, 1]
        return cam.cpu(), index

    @staticmethod
    def overlay(image: Image.Image, cam: torch.Tensor) -> Image.Image:
        """Superpose la carte de chaleur (rouge = zone qui a décidé) sur la photo d'origine."""
        import matplotlib.pyplot as plt  # import local : uniquement pour la visualisation

        cam_np = cam.numpy()
        heatmap = plt.cm.jet(cam_np)[..., :3]
        heatmap = Image.fromarray((heatmap * 255).astype("uint8")).resize(image.size, Image.BILINEAR)
        blended = Image.blend(image.convert("RGB"), heatmap, alpha=0.45)
        return blended


# --- Calibration (temperature scaling) ---------------------------------------------

def find_temperature(logits: torch.Tensor, labels: torch.Tensor) -> float:
    """Température T qui minimise la NLL sur le jeu de validation (Guo et al. 2017).

    probs_calibrées = softmax(logits / T). T > 1 -> probabilités plus prudentes,
    T < 1 -> modèle sous-confiant, on les remonte.
    ATTENTION : le log_softmax doit être recalculé APRÈS la division par T.
    """
    temperatures = torch.exp(torch.linspace(torch.log(torch.tensor(0.05)), torch.log(torch.tensor(20.0)), 400))
    best_t, best_nll = 1.0, float("inf")
    for t in temperatures:
        nll = nn.functional.nll_loss(torch.log_softmax(logits / t, dim=1), labels).item()
        if nll < best_nll:
            best_nll, best_t = nll, t.item()
    return best_t


def expected_calibration_error(probs: torch.Tensor, labels: torch.Tensor, n_bins: int = 15) -> float:
    """ECE : écart moyen entre confiance annoncée et précision réelle (plus petit = mieux)."""
    confidence, predictions = probs.max(dim=1)
    correct = (predictions == labels).float()
    ece = 0.0
    for bin_low, bin_high in zip(np.linspace(0, 1, n_bins + 1)[:-1], np.linspace(0, 1, n_bins + 1)[1:]):
        in_bin = (confidence > bin_low) & (confidence <= bin_high)
        if in_bin.any():
            ece += in_bin.float().sum().item() / len(labels) * abs(correct[in_bin].mean().item() - confidence[in_bin].mean().item())
    return ece


def calibrated_probs(logits: torch.Tensor, temperature: float) -> torch.Tensor:
    return torch.softmax(logits / temperature, dim=1)


# --- Exports ------------------------------------------------------------------------

def export_all(model: nn.Module, out_dir: str | Path, val_logits: torch.Tensor, val_labels: torch.Tensor,
               class_names: list[str], metadata: dict) -> dict[str, Path]:
    """Exporte tout ce que l'API et mobile attendent, dans models/m1/ :

    - model.pt      TorchScript (tracé) — chargé par ai-services/m1-disease
    - model_full.pt state_dict complet — reconstruit le modèle eager pour Grad-CAM à l'inférence
    - model.onnx    ONNX opset 17 (batch dynamique)
    - model.tflite  TFLite float32 (via onnx2tf + TensorFlow) pour Android
    - classes.json, calibration.json (T), metadata.json (métriques, seed, versions)
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model = model.eval()
    # Le Grad-CAM laisse des hooks sur le modèle ; torch.jit.trace les refuse.
    # On les détache proprement (aucun effet sur les poids ni les sorties).
    for module in model.modules():
        module._backward_hooks.clear()
        module._forward_hooks.clear()
        module._forward_pre_hooks.clear()
    example = torch.randn(1, 3, IMG_SIZE, IMG_SIZE)

    # 1) TorchScript pour l'API (sortie = logits, la calibration se fait côté service).
    scripted = torch.jit.trace(model, example)
    torch.jit.save(scripted, str(out_dir / "model.pt"))

    # 2) Poids complets pour le Grad-CAM en production (hooks impossibles sur TorchScript).
    torch.save(model.state_dict(), out_dir / "model_full.pt")

    # 3) ONNX.
    onnx_path = out_dir / "model.onnx"
    try:
        torch.onnx.export(model, example, str(onnx_path), opset_version=17,
                          input_names=["image"], output_names=["logits"],
                          dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}})
    except Exception as e:  # onnx / onnxscript absents : l'API n'en a pas besoin (elle lit model.pt)
        print(f"[avertissement] export ONNX ignoré : {e}")

    # 4) TFLite pour Android (chaîne ONNX -> TF -> TFLite, la plus fiable sous Colab).
    tflite_path = out_dir / "model.tflite"
    try:
        import onnx2tf

        tmp = out_dir / "_tf_tmp"
        onnx2tf.convert(input_onnx_file_path=str(onnx_path), output_folder_path=str(tmp), non_verbose=True)
        produced = tmp / "model_float32.tflite"
        if produced.exists():
            produced.replace(tflite_path)
        import shutil

        shutil.rmtree(tmp, ignore_errors=True)
    except Exception as e:  # tensorflow/onnx2tf absents ou incompatibles : on ne bloque pas l'export
        tflite_path = None
        print(f"[avertissement] export TFLite ignoré : {e}")

    # 5) Petits fichiers de configuration lus par le service.
    temperature = find_temperature(val_logits, val_labels)
    (out_dir / "classes.json").write_text(json.dumps(class_names, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "calibration.json").write_text(json.dumps({"temperature": round(temperature, 6)}, indent=2), encoding="utf-8")
    metadata = {**metadata, "seed": SEED, "img_size": IMG_SIZE, "temperature": round(temperature, 6),
                "classes": class_names}
    (out_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    names = ["model.pt", "model_full.pt", "model.onnx", "classes.json", "calibration.json", "metadata.json"]
    exported = {name: out_dir / name for name in names if (out_dir / name).exists()}
    if tflite_path is not None:
        exported["model.tflite"] = tflite_path
    return exported
