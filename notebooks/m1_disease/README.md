# M1 · Leaf diseases — notebooks

| | |
|---|---|
| Data | Uğuz & Uysal — `Olive_Leaf_Disease_Datasets_After_Preprocessing` (3 classes, ~7 000 images) |
| Baseline | Petit CNN (3 blocs conv, aucun transfert) |
| Modèle principal | MobileNetV3-Large ImageNet, fine-tuning en 2 phases (tête puis complet) |
| Fiabilité | Temperature scaling (T apprise sur val) + seuil de confiance 0.70 |
| Métriques | Accuracy, F1 par classe + macro, matrices de confusion, Grad-CAM, ECE |
| Export | `models/m1/` : `model.pt` (TorchScript), `model.onnx`, `model.tflite`, `classes.json`, `calibration.json`, `metadata.json` |

## Résultats du modèle servi (entraîné le 17/10/2026)

Jeu : **Olive Leaf Image Dataset** (Kaggle, Uğuz & Uysal) : 3 400 images, 3 classes. Splits 70/15/15 groupés par
feuille d'origine (seed 42) : 2 380 train / 512 val / 508 test. Entraînement CPU : petit CNN 6 époques,
MobileNetV3 4 + 6 époques (`M1_EPOCHS_*`), torch 2.11 (la même version que le service).

| Modèle (test, 508 photos jamais vues) | Accuracy | F1 saine | F1 œil de paon | F1 Aculus | F1 macro |
|---|---|---|---|---|---|
| Petit CNN (baseline) | 75,2 % | 0,723 | 0,821 | 0,680 | 0,741 |
| **MobileNetV3 (servi)** | **97,1 %** | **0,964** | **0,977** | **0,967** | **0,969** |

- Calibration : T = 0,49 ; ECE de 0,045 à 0,020.
- Seuil 0,70 : 15 photos sur 508 refusées (« photo peu claire ») ; accuracy de **98,2 %** sur les photos acceptées
  (60 % sur les refusées : le modèle se trompe surtout quand il n'est pas sûr).
- Exports produits : `model.pt` + `model_full.pt` (Grad-CAM), `classes.json`, `calibration.json`, `metadata.json`.
  ONNX et TFLite ont été sautés (`onnxscript`, TensorFlow absents) : l'API ne les utilise pas.

### Relancer en local sans Colab (Docker, depuis la racine du repo)

```bash
docker run --rm --shm-size=2g -v "${PWD}:/repo" -v "C:/chemin/vers/dataset:/data/olive-leaf:ro" -w /repo/notebooks/m1_disease -e M1_DATA_SRC=/data/olive-leaf -e M1_EPOCHS_PHASE2=6 -e M1_TFLITE=0 <image avec torch 2.11 + torchvision 0.26 + jupyter> jupyter nbconvert --to notebook --execute train_m1.ipynb --output outputs/train_m1_executed.ipynb
```

Variables : `M1_DATA_SRC` (dossier du dataset, découpé ou non), `M1_EPOCHS_BASELINE` / `M1_EPOCHS_PHASE1` /
`M1_EPOCHS_PHASE2`, `M1_TFLITE=0` (pas de TensorFlow). Ensuite : `docker compose restart m1-disease`.

## Fichiers

| Fichier | Rôle |
|---|---|
| `prepare_splits.py` | Détecte les dossiers de classes et crée les splits **70/15/15 stratifiés, seed 42**, **groupés par feuille d'origine** (les variantes Roboflow d'une même feuille restent dans le même split — pas de fuite de données). Sortie : `data/processed/m1_disease/{train,val,test}/<classe>/`. |
| `m1_common.py` | Bibliothèque partagée : seeds, augmentations « photo terrain », datasets, modèles, boucle d'entraînement, métriques, Grad-CAM, calibration, exports. Importé par le notebook et `evaluate_field.py`. |
| `train_m1.ipynb` | Tout le pipeline : splits → EDA → baseline → MobileNetV3 → évaluation → calibration → seuil → export. |
| `evaluate_field.py` | Évalue le modèle exporté sur des photos terrain (`field_test/`) avec les mêmes métriques que l'API. |

## 1 · Préparer les données (une seule fois)

```bash
cd notebooks/m1_disease
python prepare_splits.py --src "C:/.../Olive_Leaf_Disease_Datasets_After_Preprocessing"
# splits -> <repo>/data/processed/m1_disease/ (idempotent : relancer ne fait rien sans --force)
```

## 2 · Entraîner (Google Colab recommandé, T4 GPU)

1. Copiez dans votre Drive :
   - le dataset sous `ZitounAI/Olive_Leaf_Disease_Datasets_After_Preprocessing/` ;
   - `train_m1.ipynb`, `m1_common.py`, `prepare_splits.py` sous `ZitounAI/notebooks/m1_disease/`.
2. Ouvrez `train_m1.ipynb` dans Colab : `Exécution → Modifier le type d'exécution → T4 GPU`.
3. Exécutez de haut en bas (~30–40 min sur T4). Le notebook détecte Colab tout seul,
   monte le Drive, prépare les splits localement puis entraîne.
4. La dernière cellule produit un zip des artefacts : téléchargez-le, dézippez-le dans
   `models/m1/` du repo, puis partagez-le : `python scripts/models.py push m1`
   (voir `models/README.md`, il faut `HF_MODELS_REPO` et `HF_TOKEN` dans `.env`).

En local (CPU possible) : exécutez le notebook depuis ce dossier avec les epochs réduits
(cellule de configuration) — comptez quelques heures sur CPU pour la version complète.

## 3 · Évaluer sur photos terrain

```bash
mkdir -p field_test/healthy field_test/peacock_spot field_test/aculus_olearius
# … déposez-y les photos prises chez les agriculteurs (ou à plat dans field_test/)
python evaluate_field.py          # rapport -> outputs/field_report/ (CSV + JSON + matrice)
```

## Conventions équipe

- Les notebooks s'exécutent de haut en bas sur un noyau frais ; **sorties dépouillées avant commit** (CONTRIBUTING.md).
- Figures produites dans `outputs/` et données dans `data/` : **jamais commités**.
- Le résultat attendu par l'équipe : `models/m1/model.pt` (+ fichiers annexes) sur Hugging Face.
