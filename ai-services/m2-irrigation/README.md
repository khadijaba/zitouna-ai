# M2 · Irrigation & weather alerts

**Owner:** Membre 2 · **Type:** Time series (LSTM and Prophet vs "same day last year")

Thin FastAPI service: it loads the trained model and exposes `POST /predict`. No business logic, no database — that lives in the Spring backend.

| | |
|---|---|
| Endpoint | `POST /predict` — input: JSON `{latitude, longitude, treeCount?, areaHa?, days}` (days ≤ 16) |
| Health | `GET /health` → `{"status", "module", "modelLoaded"}` |
| Contract | [docs/api-contract.md](../../docs/api-contract.md) (section M2) |
| Port (local / compose) | `8002` |
| Model files | `models/m2/lstm_et0.npz` (weights + normalisation) · `metadata.json` (metrics) — not in Git |
| Training notebook | [`notebooks/m2_irrigation/`](../../notebooks/m2_irrigation/) |
| External data | [Open-Meteo](https://open-meteo.com) forecast API, free, no key (internet needed) |

## How a request is answered

1. Open-Meteo (`api.open-meteo.com/v1/forecast`, `past_days=30`) for the parcel: the **last 30 days**
   (ET₀, rain, Tmax, Tmin) and the **coming days** (rain, Tmax, Tmin). Cached 1 h per ~10 km cell.
2. **LSTM** (30 days → ET₀ of the next 16 days), computed in NumPy: no PyTorch in the image. The forward
   pass is checked against PyTorch in the notebook (max gap ~1e-6 mm/day).
3. **FAO-56 water balance**: `need = ET₀ × 0.65 − 0.8 × rain`, irrigate if `need ≥ 2 mm`,
   litres per tree = need × m² per tree. **Alerts**: frost if Tmin ≤ 0 °C (HIGH ≤ −2 °C), heatwave if
   Tmax ≥ 40 °C (HIGH ≥ 44 °C), from the Open-Meteo forecast.

Rain and temperatures come from the numerical weather forecast on purpose: no statistical model trained on
past weather predicts rain better than a weather model. The ML part is the ET₀ forecast.

## Mock mode

Without `models/m2/lstm_et0.npz`, **or when Open-Meteo cannot be reached**, the service answers with
synthetic weather and `"mock": true` (the app shows the "données de démo" badge). The backend and the app
keep working.

| Env | Default | Role |
|---|---|---|
| `MODEL_DIR` | `../../models/m2` (Docker: `/models/m2`) | model folder |
| `MODEL_VERSION` | `lstm-et0` | returned in `modelVersion` |
| `OPEN_METEO_URL` | `https://api.open-meteo.com/v1/forecast` | weather API |
| `M2_WEATHER_TIMEOUT` | `8` | seconds per Open-Meteo call (2 attempts) |

## Run locally

```bash
cd ai-services/m2-irrigation
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r ../requirements-dev.txt
uvicorn app.main:app --reload --port 8002   # health: http://localhost:8002/health
python -m pytest
```

The tests use a small random LSTM and a fake Open-Meteo answer: they need no network and no trained model.

Do not change the response schema in `app/schemas.py` without updating the contract and telling the backend owner (see [CONTRIBUTING.md](../../CONTRIBUTING.md#changing-the-api-contract)).
