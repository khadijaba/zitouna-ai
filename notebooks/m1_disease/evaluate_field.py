"""M1 · Évaluation terrain : teste le modèle exporté sur des photos réelles d'agriculteurs.

Rangez vos photos dans notebooks/m1_disease/field_test/ :

    field_test/healthy/*.jpg        (si vous connaissez la vérité terrain)
    field_test/peacock_spot/*.jpg
    field_test/aculus_olearius/*.jpg

… ou toutes à plat dans field_test/ si vous ne connaissez pas la classe (prédictions seules).

Le script utilise EXACTEMENT le même chemin de code que l'API : modèle TorchScript
models/m1/model.pt, prétraitement identique, temperature scaling (calibration.json),
seuil de confiance 0.70 (photos « peu claires » signalées comme telles).

Utilisation :

    python evaluate_field.py                                  # défauts : field_test/ et <repo>/models/m1
    python evaluate_field.py --field-dir ... --models-dir ...
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import torch
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import m1_common as mc  # noqa: E402
from prepare_splits import detect_class  # noqa: E402 — même détection de classes que pour les splits

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def load_export(models_dir: Path) -> tuple[torch.jit.ScriptModule, list[str], float]:
    """Charge model.pt (TorchScript) + classes.json + calibration.json, comme l'API."""
    model_path = models_dir / "model.pt"
    if not model_path.exists():
        sys.exit(f"[erreur] {model_path} introuvable — lancez d'abord le notebook (cellule export).")
    model = torch.jit.load(str(model_path), map_location="cpu")
    model.eval()
    classes = mc.CLASSES
    if (models_dir / "classes.json").exists():
        classes = json.loads((models_dir / "classes.json").read_text(encoding="utf-8"))
    temperature = 1.0
    if (models_dir / "calibration.json").exists():
        temperature = json.loads((models_dir / "calibration.json").read_text(encoding="utf-8")).get("temperature", 1.0)
    return model, classes, temperature


def collect_field_images(field_dir: Path) -> list[tuple[Path, str | None]]:
    """[(chemin, classe réelle ou None)] — classe reconnue via le nom du sous-dossier."""
    images: list[tuple[Path, str | None]] = []
    for path in sorted(field_dir.rglob("*")):
        if path.suffix.lower() in IMAGE_EXTENSIONS:
            truth = detect_class(path.parent.name) if path.parent != field_dir else None
            images.append((path, truth if truth in mc.CLASSES else None))
    return images


def main() -> int:
    parser = argparse.ArgumentParser(description="Évaluation terrain du modèle M1.")
    parser.add_argument("--field-dir", default=str(HERE / "field_test"),
                        help="dossier de photos terrain (sous-dossiers par classe ou images à plat)")
    parser.add_argument("--models-dir", default=str(HERE.parents[1] / "models" / "m1"),
                        help="dossier d'export du modèle (défaut : <repo>/models/m1)")
    parser.add_argument("--threshold", type=float, default=mc.LOW_CONFIDENCE_THRESHOLD)
    args = parser.parse_args()

    field_dir, models_dir = Path(args.field_dir), Path(args.models_dir)
    if not field_dir.is_dir():
        sys.exit(f"[erreur] dossier introuvable : {field_dir}\n"
                 f"Créez-le avec vos photos : {field_dir}/<classe>/*.jpg")
    model, classes, temperature = load_export(models_dir)
    transform = mc.build_transforms(train=False)  # même prétraitement que l'API

    images = collect_field_images(field_dir)
    if not images:
        sys.exit(f"[erreur] aucune image dans {field_dir}")

    # Prédiction de chaque photo : logits TorchScript -> calibration -> seuil de confiance.
    rows: list[dict] = []
    preds: list[int] = []
    for path, truth in images:
        image = Image.open(path).convert("RGB")
        with torch.no_grad():
            logits = model(transform(image).unsqueeze(0))
        probs = mc.calibrated_probs(logits, temperature)[0]
        confidence, index = float(probs.max()), int(probs.argmax())
        preds.append(index)
        rows.append({"fichier": path.name,
                     "verite": truth or "-",
                     "predit": classes[index],
                     "confiance": round(confidence, 4),
                     "peu_claire": "oui" if confidence < args.threshold else "non"})

    n = len(rows)
    n_low = sum(1 for r in rows if r["peu_claire"] == "oui")
    print(f"{n} photos chargées, température T = {temperature}.")
    print(f"Photos « peu claires » (confiance < {args.threshold:.0%}) : {n_low}/{n} ({n_low / n:.0%})")

    out_dir = HERE / "outputs" / "field_report"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "previsions.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["fichier", "verite", "predit", "confiance", "peu_claire"])
        writer.writeheader()
        writer.writerows(rows)

    summary: dict = {"n_photos": n, "threshold": args.threshold, "temperature": temperature,
                     "taux_peu_claires": round(n_low / n, 4)}

    labeled_idx = [i for i, (_, truth) in enumerate(images) if truth is not None]
    if labeled_idx:
        labels = torch.tensor([classes.index(images[i][1]) for i in labeled_idx])
        preds_lab = torch.tensor([preds[i] for i in labeled_idx])
        confs = torch.tensor([rows[i]["confiance"] for i in labeled_idx])
        report = mc.classification_report_dict(torch.eye(len(classes))[preds_lab], labels, classes)
        print(f"\nMétriques sur les {len(labeled_idx)} photos étiquetées :")
        for key, value in report.items():
            print(f"  {key:22s} {value}")
        keep = confs >= args.threshold
        if keep.all():
            print("  (aucune photo refusée par le seuil)")
        else:
            acc_kept = (preds_lab[keep] == labels[keep]).float().mean().item()
            acc_rej = (preds_lab[~keep] == labels[~keep]).float().mean().item()
            print(f"  accuracy photos claires   : {acc_kept:.4f} ({int(keep.sum())} photos)")
            print(f"  accuracy photos refusées  : {acc_rej:.4f} ({int((~keep).sum())} photos — le modèle "
                  "se trompe surtout là où il n'est pas sûr)")
        mc.plot_confusion(preds_lab, labels, classes, out_dir / "matrice_confusion_terrain.png",
                          "Évaluation terrain — matrice de confusion")
        summary["rapport_etiquete"] = report
    else:
        print("\nAucune vérité terrain (images à plat) : prédictions détaillées dans le CSV.")

    (out_dir / "synthese.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[fait] rapport  : {out_dir / 'previsions.csv'}")
    print(f"[fait] synthèse : {out_dir / 'synthese.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
