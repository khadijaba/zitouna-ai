# Trained models

Weights are **not in Git**. They are shared through one private Hugging Face model repo, with the same folders as here. `docker-compose.yml` mounts this folder read-only into each AI container at `/models`.

```bash
pip install huggingface_hub
# in .env: HF_MODELS_REPO=<user-or-org>/zitouna-models and HF_TOKEN=hf_... (huggingface.co/settings/tokens)
python scripts/models.py list                 # what is on the Hub
python scripts/models.py pull                 # download everything into models/
python scripts/models.py push m5_ensemble     # module owner: upload after (re)training
docker compose restart                        # the services load the new weights at startup
```

To give teammates access to the private repo, create a free Hugging Face **organization**, move the repo into it (`HF_MODELS_REPO=<org>/zitouna-models`) and invite them; each one uses their own token.

| Module | Expected file | Loaded by |
|---|---|---|
| M1 | `models/m1/model.pt` | `ai-services/m1-disease/app/predictor.py` |
| M2 | `models/m2/lstm_et0.npz` (+ `metadata.json`) | `ai-services/m2-irrigation/app/predictor.py` |
| M3 | `models/m3/model.joblib` + `history.csv` + `metadata.json` | `ai-services/m3-yield/app/predictor.py` |
| M4 | `models/m4/model.json` + `prices.csv` (+ `metadata.json`) | `ai-services/m4-price/app/predictor.py` |
| M5 | `models/m5_ensemble/` (`config.json`, `tfidf.joblib`; `setfit/` only if `weight_setfit > 0`) | `ai-services/m5-assistant/app/predictor.py` |
| M6 | none for the OpenCV detector · `models/m6/best.pt` for a fine-tuned YOLOv8 | `ai-services/m6-tree-count/app/predictor.py` |

Every file is produced by the module's notebook in `notebooks/` (run it to regenerate). If a file is missing, the
service runs in mock mode (`"mock": true`). Put the model version (e.g. the MLflow run id) in the `MODEL_VERSION` environment variable.
