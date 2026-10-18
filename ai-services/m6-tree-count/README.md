# M6 · Olive tree counting

**Owner:** Membre 6 · **Type:** Vision — classical crown detection with OpenCV (YOLOv8 when trained)

Thin FastAPI service: it loads the detector and exposes `POST /predict`. No business logic, no database — that lives in the Spring backend.

| | |
|---|---|
| Endpoint | `POST /predict` — input: multipart `image` (drone or satellite view, top-down) |
| Health | `GET /health` → `{"status", "module", "modelLoaded"}` |
| Contract | [docs/api-contract.md](../../docs/api-contract.md) (section M6) |
| Port (local / compose) | `8006` |
| Detector | OpenCV (no file needed) · `models/m6/best.pt` (YOLOv8) used instead if present and `ultralytics` installed |
| Notebook / method | [`notebooks/m6_tree_count/`](../../notebooks/m6_tree_count/) |

## Detector

Vegetation score (excess green + darkness) → Otsu threshold → morphological cleaning → typical crown radius
(median blob) → distance transform + local maxima ≥ 1 radius apart: one tree per maximum, touching crowns are
split. `modelVersion` = `opencv-crowns-1.0`, `mock: false`. Mock mode (regular grid) only if OpenCV is missing.

## Run locally

```bash
cd ai-services/m6-tree-count
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r ../requirements-dev.txt
uvicorn app.main:app --reload --port 8006   # health: http://localhost:8006/health
python -m pytest
```

The tests draw synthetic orchards with a known number of trees (separate and touching crowns, bare soil) and
check the count (≤ 5 % error on separate trees, ≤ 10 % on touching crowns).

Do not change the response schema in `app/schemas.py` without updating the contract and telling the backend owner (see [CONTRIBUTING.md](../../CONTRIBUTING.md#changing-the-api-contract)).
