"""M1 · Préparation des données : détection des classes + splits train/val/test 70/15/15.

Le dataset Uğuz & Uysal est livré en un seul dossier par classe (pas de split) :

    Olive_Leaf_Disease_Datasets_After_Preprocessing/
        Aculus Olive/ *.jpg
        Healthy/      *.jpg
        olivepeacockspot/ *.jpg

ATTENTION fuite de données : Roboflow ajoute plusieurs variantes de la MÊME feuille
(nommage « <base>_jpg.rf.<hash>.jpg »). On regroupe donc les images par feuille d'origine :
toutes les variantes d'une feuille restent dans le même split.

Utilisation (depuis notebooks/m1_disease/) :

    python prepare_splits.py --src "C:/.../Olive_Leaf_Disease_Datasets_After_Preprocessing"
    python prepare_splits.py --src ... --dest ../../data/processed/m1_disease --seed 42

Sortie : dest/train/<classe>/, dest/val/<classe>/, dest/test/<classe>/ + manifest.json.
Idempotent : si les splits existent déjà (et --force absent), le script ne fait rien.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

# Classes du contrat M1 (docs/api-contract.md). olive_knot : pas dans ce dataset,
# gardé dans le contrat pour le futur.
CLASS_ALIASES = {
    "healthy": ["healthy", "saine", "feuillesaine", "sain"],
    "peacock_spot": ["peacock", "peacockspot", "œildepaon", "oeildepaon", "olivepeacock"],
    "aculus_olearius": ["aculus", "aculusolearius", "aculusolive", "acarien"],
    "olive_knot": ["knot", "tuberculose", "oliveknot"],
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
ROBOFLOW_SUFFIX = re.compile(r"^(?P<base>.+?)_(?:jpg|jpeg|png|bmp)\.rf\.[0-9a-f]+$", re.IGNORECASE)


def normalize(name: str) -> str:
    """minuscules, sans espaces ni tirets ni underscores — pour reconnaître les dossiers."""
    return re.sub(r"[\s_\-]+", "", name).lower()


def detect_class(folder_name: str) -> str | None:
    """Renvoie la classe du contrat à partir du nom de dossier (ex: 'Aculus Olive')."""
    norm = normalize(folder_name)
    for class_name, aliases in CLASS_ALIASES.items():
        if any(alias in norm for alias in aliases):
            return class_name
    return None


def leaf_group(filename: str) -> str:
    """Groupe = feuille d'origine. 'A163_jpg.rf.abc123.jpg' et 'A163.jpg' -> 'A163'."""
    stem = Path(filename).stem
    match = ROBOFLOW_SUFFIX.match(stem)
    return match.group("base") if match else stem


def collect_images(src: Path) -> dict[str, list[Path]]:
    """Parcourt src (1 ou 2 niveaux de profondeur) et range les images par classe."""
    found: dict[str, list[Path]] = defaultdict(list)
    for folder in sorted(p for p in src.iterdir() if p.is_dir()):
        class_name = detect_class(folder.name)
        if class_name is None:
            # Cas dataset déjà splitté : src/train/<classe>, src/val/<classe>...
            for sub in sorted(p for p in folder.iterdir() if p.is_dir()):
                sub_class = detect_class(sub.name)
                if sub_class:
                    found[sub_class].extend(_images_in(sub))
                    print(f"  {folder.name}/{sub.name} -> {sub_class}")
                elif sub.name.lower() not in {"train", "val", "test"}:
                    print(f"  [ignoré] dossier non reconnu : {folder.name}/{sub.name}")
            continue
        images = _images_in(folder)
        if images:
            found[class_name].extend(images)
            print(f"  {folder.name} -> {class_name} ({len(images)} images)")
    return found


def _images_in(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS)


def stratified_group_split(images: dict[str, list[Path]], seed: int,
                           ratios: tuple[float, float, float]) -> dict[str, dict[str, list[Path]]]:
    """Split 70/15/15 stratifié PAR GROUPE (feuille d'origine), ordre déterministe."""
    rng = random.Random(seed)
    splits: dict[str, dict[str, list[Path]]] = {"train": {}, "val": {}, "test": {}}
    for class_name, paths in images.items():
        groups: dict[str, list[Path]] = defaultdict(list)
        for path in paths:
            groups[leaf_group(path.name)].append(path)
        group_names = sorted(groups)
        rng.shuffle(group_names)
        n_images = len(paths)
        assigned = {"train": [], "val": [], "test": []}
        counts = {"train": 0, "val": 0, "test": 0}
        cumulative = 0
        for name in group_names:  # fraction cumulée < 70% -> train, < 85% -> val, sinon -> test
            size = len(groups[name])
            fraction = cumulative / n_images
            if fraction < ratios[0]:
                bucket = "train"
            elif fraction < ratios[0] + ratios[1]:
                bucket = "val"
            else:
                bucket = "test"
            assigned[bucket].extend(groups[name])
            counts[bucket] += size
            cumulative += size
        for bucket, paths_in in assigned.items():
            splits[bucket][class_name] = paths_in
        print(f"  {class_name}: {counts['train']} train / {counts['val']} val / "
              f"{counts['test']} test  ({len(group_names)} feuilles distinctes)")
    return splits


def copy_splits(splits: dict[str, dict[str, list[Path]]], dest: Path) -> None:
    for bucket, classes in splits.items():
        for class_name, paths in classes.items():
            out_dir = dest / bucket / class_name
            out_dir.mkdir(parents=True, exist_ok=True)
            for path in paths:
                target = out_dir / path.name
                if target.exists():  # deux feuilles d'origines différentes, même nom de fichier
                    target = out_dir / f"{path.stem}_{len(path.name)}{path.suffix}"
                shutil.copy2(path, target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Splits train/val/test 70/15/15 pour M1 (seed fixe, par feuille).")
    parser.add_argument("--src", required=True, help="dossier du dataset téléchargé (un sous-dossier par classe)")
    parser.add_argument("--dest", default=str(Path(__file__).resolve().parents[2] / "data" / "processed" / "m1_disease"),
                        help="dossier de sortie (défaut : <repo>/data/processed/m1_disease)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true", help="écraser des splits existants")
    args = parser.parse_args()

    src, dest = Path(args.src), Path(args.dest)
    if not src.is_dir():
        print(f"[erreur] dossier source introuvable : {src}")
        return 1
    manifest = dest / "manifest.json"
    if (dest / "train").is_dir() and not args.force:
        print(f"[ok] splits déjà présents dans {dest} — rien à faire (--force pour reconstruire).")
        return 0

    print(f"Source : {src}")
    images = collect_images(src)
    if not images:
        print("[erreur] aucune image trouvée — vérifiez --src (attendu : un sous-dossier par classe).")
        return 1
    print(f"\nRépartition (seed {args.seed}, groupes = feuilles d'origine) :")
    splits = stratified_group_split(images, args.seed, (0.70, 0.15, 0.15))

    if dest.exists():
        shutil.rmtree(dest)
    print(f"\nCopie vers {dest} ...")
    copy_splits(splits, dest)
    manifest.write_text(json.dumps({
        "source": str(src), "seed": args.seed, "ratios": [0.70, 0.15, 0.15],
        "counts": {b: {c: len(p) for c, p in classes.items()} for b, classes in splits.items()},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(p) for classes in splits.values() for p in classes.values())
    print(f"[fait] {total} images copiées. Manifest : {manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
