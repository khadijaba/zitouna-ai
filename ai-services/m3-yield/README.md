# M3 · Yield forecast

**Owner:** Membre 3 · **Type:** Tabular regression (Random Forest vs linear regression), national scope (roadmap plan B)

Thin FastAPI service: it loads the trained model and exposes `POST /predict`. No business logic, no database — that lives in the Spring backend.

| | |
|---|---|
| Endpoint | `POST /predict` — input: JSON `{governorate, season, treeCount?, areaHa?}` |
| Health | `GET /health` → `{"status", "module", "modelLoaded"}` |
| Contract | [docs/api-contract.md](../../docs/api-contract.md) (section M3) |
| Port (local / compose) | `8003` |
| Model files | `models/m3/model.joblib` · `history.csv` (FAOSTAT + seasonal ERA5) · `metadata.json` — not in Git |
| Training notebook | [`notebooks/m3_yield/`](../../notebooks/m3_yield/) (results, data sources, limits) |

## How a request is answered

- `regionalProductionTonnes` is the **national** production of Tunisia (`scope: "NATIONAL"`): the published
  FAOSTAT figure if the season is known (`observed: true`), otherwise the Random Forest forecast (seasons after
  the last FAOSTAT year are forecast one after the other).
- Parcel: national yield per hectare × `areaHa`; without area, national production / ~100 million trees ×
  `treeCount`. `parcelLowKg` / `parcelHighKg` come from the real errors of the rolling test (10 % / 90 %).

Without `models/m3/model.joblib` the service answers with rough regional figures and `"mock": true`.

## Run locally

```bash
cd ai-services/m3-yield
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r ../requirements-dev.txt
uvicorn app.main:app --reload --port 8003   # health: http://localhost:8003/health
python -m pytest
```

The tests fit a small linear model on a synthetic history (same files as the notebook): published season,
recursive forecast, area vs tree count, interval, HTTP endpoint.

Do not change the response schema in `app/schemas.py` without updating the contract and telling the backend owner (see [CONTRIBUTING.md](../../CONTRIBUTING.md#changing-the-api-contract)).
