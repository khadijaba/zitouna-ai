# M1 · Guide Colab — de l'entraînement au diagnostic dans l'app

## Étape 0 · Préparation (5 minutes, une seule fois)

1. **Le zip du dataset est prêt** : `olive_leaf_dataset.zip` (89 Mo), créé à côté du projet.
2. Dans **Google Drive**, créez `ZitounAI/notebooks/m1_disease/` et copiez-y les 3 fichiers
   du dossier `notebooks/m1_disease/` du repo : `train_m1.ipynb`, `m1_common.py`, `prepare_splits.py`.

## Étape 1 · Entraîner sur Colab (~30–40 min sur T4)

1. Ouvrez https://colab.research.google.com → **Fichier → Ouvrir un notebook → Drive** → `train_m1.ipynb`.
2. **Exécution → Modifier le type d'exécution → T4 GPU**.
3. Exécutez la **première cellule** (elle monte le Drive).
4. **Méthode A (recommandée) — le zip passe par Drive** : sur drive.google.com, glissez
   `olive_leaf_dataset.zip` dans le dossier `ZitounAI/`, puis exécutez dans le notebook :

   ```python
   !unzip -q /content/drive/MyDrive/ZitounAI/olive_leaf_dataset.zip -d /content/
   DATA_SRC = Path("/content/Olive_Leaf_Disease_Datasets_After_Preprocessing")
   print("dataset prêt :", DATA_SRC.exists())
   ```

   **Méthode B — panneau Fichiers du notebook** (icône 📁 à gauche du notebook **ouvert**,
   jamais la page d'accueil de Colab qui, elle, n'accepte que des .ipynb et renvoie une erreur
   `Unexpected token 'P', "PK"` sur un zip) : bouton Importer → le zip → puis :

   ```python
   !unzip -q /content/olive_leaf_dataset.zip -d /content/
   DATA_SRC = Path("/content/Olive_Leaf_Disease_Datasets_After_Preprocessing")
   print("dataset prêt :", DATA_SRC.exists())
   ```

5. Exécutez **toutes les cellules de haut en bas**. Points de contrôle :
   - splits : ~4 900 train / ~1 000 val / ~1 000 test ;
   - MobileNetV3 : le F1 macro val monte au-dessus de 0.9 après la phase 2 ;
   - export : la dernière cellule produit `/content/models_m1.zip` → **téléchargez-le**
     (clic droit dans le panneau Fichiers).

## Étape 2 · Installer le modèle sur votre PC

```bash
cd C:\Users\LENOVO\.zcode\workspace\default\ZitounAI
# dézipper models_m1.zip -> models/m1/ (model.pt, model_full.pt, model.onnx, model.tflite,
#                                        classes.json, calibration.json, metadata.json)
```

## Étape 3 · Partager avec l'équipe (Hugging Face, optionnel mais recommandé)

1. Compte gratuit https://huggingface.co → créer un **token** (Settings → Access Tokens, rôle write).
2. Dans `ZitounAI/.env` (copiez `.env.example` si besoin) :

   ```ini
   HF_MODELS_REPO=votre-user/zitouna-models     # créez le repo vide sur huggingface.co (type model, private)
   HF_TOKEN=hf_votre_token
   ```

3. `pip install huggingface_hub` puis `python scripts/models.py push m1`
   → les coéquipiers récupèrent tout avec `python scripts/models.py pull`.

## Étape 4 · Lancer l'API (sans Docker, comme le backend dans IntelliJ)

```bash
cd ZitounAI\ai-services\m1-disease
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt        # torch CPU ~200 Mo, quelques minutes
uvicorn app.main:app --port 8001       # http://localhost:8001/health
```

`GET /health` doit répondre `"modelLoaded": true`. **Sans backend lancé**, testez directement
dans l'application (page Diagnostic) ou : `curl -F image=@feuille.jpg http://localhost:8001/predict`.

## Étape 5 · Tester dans l'application

Relancez simplement votre **backend** (IntelliJ) et le **frontend** : le backend appelle
`http://localhost:8001` (valeur par défaut `AI_M1_URL`) → page de diagnostic → envoyez la photo
d'une feuille → maladie + confiance + conseil (+ « photo peu claire » si confiance < 70 %).
