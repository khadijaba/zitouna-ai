# M1 · Leaf diseases

**Owner:** Membre 1 · **Type:** Vision — classification (MobileNetV3-Large vs petit CNN, Grad-CAM, calibration)

Thin FastAPI service: it loads the trained model and exposes `POST /predict`. No business logic, no database — that lives in the Spring backend.

| | |
|---|---|
| Endpoint | `POST /predict` — input: multipart `image` (JPEG/PNG d'une feuille) |
| Health | `GET /health` → `{"status", "module", "modelLoaded"}` |
| Contract | [docs/api-contract.md](../../docs/api-contract.md) (section M1) |
| Port (local / compose) | `8001` |
| Model files | `models/m1/` : `model.pt` (TorchScript) · `classes.json` · `calibration.json` · `model_full.pt` (Grad-CAM, optionnel) |
| Training notebook | [`notebooks/m1_disease/`](../../notebooks/m1_disease/) |
| Advice data | [`app/treatments.json`](app/treatments.json) — description, conseil, avertissement par classe |

## Run locally

```bash
cd ai-services/m1-disease
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r ../requirements-dev.txt   # torch CPU ~200 Mo, prévoir quelques minutes
uvicorn app.main:app --reload --port 8001   # health: http://localhost:8001/health
python -m pytest
```

## Mode mock vs vrai modèle

Sans `models/m1/model.pt`, le service répond avec des **données mock** (`"mock": true`) : le backend
et l'app fonctionnent quand même. Avec le modèle (voir `notebooks/m1_disease/README.md`), la chaîne
réelle est :

photo → RGB → resize 256 → crop 224 → normalisation ImageNet → TorchScript →
**softmax(logits / T)** (temperature scaling appris sur le jeu de validation) → argmax.

**Seuil de confiance 0.70** : si la probabilité calibrée maximale est inférieure à 0.70, aucun
diagnostic n'est renvoyé — `advice` contient le message « photo peu claire, reprenez-la » (champ du
contrat, affiché par le frontend) et le champ additionnel `lowConfidence` vaut `true`
(le DTO Spring ignore ce champ inconnu ; à coordonner avec le responsable backend si on veut le
faire remonter jusqu'à l'app).

**Grad-CAM** : si `model_full.pt` est présent, chaque réponse contient `heatmapBase64` (PNG de la
zone malade superposée à la feuille). Désactivable : variable d'env `M1_HEATMAP=0`.

| Env | Défaut | Rôle |
|---|---|---|
| `MODEL_DIR` | `../../models/m1` (Docker : `/models/m1`) | dossier des artefacts |
| `MODEL_VERSION` | `dev` | ex. l'id de run MLflow, renvoyé dans `modelVersion` |
| `M1_HEATMAP` | `1` | `0` = pas de Grad-CAM (réponses plus rapides) |

## Conseils de traitement (`app/treatments.json`)

Une entrée par classe (`labelFr`, `description`, `advice`, `warning`, `source`) + l'entrée
`low_confidence`. Les conseils sont **volontairement génériques et prudents**, tous marqués
« À valider par un agronome (INRAT / ONH) » : à faire relire avant tout usage réel.
Modifier ce fichier suffit à changer les conseils, sans retoucher au code.
