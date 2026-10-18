# M4 · Price & selling time

**Owner:** Membre 4 · **Type:** Time series (SARIMA vs LSTM vs naive) + sell/store rule

Thin FastAPI service: it loads the trained model and exposes `POST /predict`. No business logic, no database — that lives in the Spring backend.

| | |
|---|---|
| Endpoint | `POST /predict` — input: JSON `{horizonWeeks, quantityKg?}` (horizon ≤ 26 weeks) |
| Health | `GET /health` → `{"status", "module", "modelLoaded"}` |
| Contract | [docs/api-contract.md](../../docs/api-contract.md) (section M4) |
| Port (local / compose) | `8004` |
| Model files | `models/m4/model.json` (SARIMA order, prudence margin, data source) · `prices.csv` (monthly series, TND/kg) · `metadata.json` (metrics) — not in Git |
| Training notebook | [`notebooks/m4_price/`](../../notebooks/m4_price/) |

## How a request is answered

1. At start-up, the SARIMA order chosen in the notebook is **re-fitted on the whole series** (`prices.csv`,
   log of the price, about one second). No pickle: no version trap between notebook and service.
2. Monthly forecast with an **80 % interval**, up to the requested horizon.
3. Monthly prices are dated the 15th; the log price is **interpolated** linearly to today (estimated current
   price, the last published month being a few months old) and to each requested week.
4. **Sell / store rule** (same as the notebook): the week that maximises `price − 0.15 TND/kg × months of storage`;
   `STORE` only if that net gain exceeds today's price by more than the **prudence margin** (`min_gain_share`
   in `model.json`, chosen on the validation years). `expectedGainTnd = net gain × quantityKg`.

The response has an additive field `source`: where the prices come from (the Spring DTO ignores it).

## Mock mode

Without `models/m4/model.json` + `prices.csv` the service answers with a synthetic price curve and
`"mock": true`.

| Env | Default | Role |
|---|---|---|
| `MODEL_DIR` | `../../models/m4` (Docker: `/models/m4`) | model folder |
| `MODEL_VERSION` | `sarima` | returned in `modelVersion` |

## Run locally

```bash
cd ai-services/m4-price
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r ../requirements-dev.txt
uvicorn app.main:app --reload --port 8004   # health: http://localhost:8004/health
python -m pytest
```

The tests build a synthetic price series (flat, rising, falling) and check the contract, the interval,
the STORE / SELL_NOW advice and the prudence margin, without the trained files.

Do not change the response schema in `app/schemas.py` without updating the contract and telling the backend owner (see [CONTRIBUTING.md](../../CONTRIBUTING.md#changing-the-api-contract)).
