# AI services

One thin FastAPI service per module. Each one loads its trained model and exposes:

- `GET /health`
- `POST /predict` (M5 exposes `POST /intent` instead)

No business logic, no database, no calls to other modules: that is the Spring backend's job.

| Service | Owner | Local port |
|---|---|---|
| [m1-disease](m1-disease/) | Membre 1 | 8001 |
| [m2-irrigation](m2-irrigation/) | Membre 2 | 8002 |
| [m3-yield](m3-yield/) | Membre 3 | 8003 |
| [m4-price](m4-price/) | Membre 4 | 8004 |
| [m5-assistant](m5-assistant/) | Membre 5 | 8005 |
| [m6-tree-count](m6-tree-count/) | Membre 6 | 8006 |

Same layout everywhere:

```
mX-name/
├── app/
│   ├── main.py        FastAPI routes (don't add logic here)
│   ├── schemas.py     request/response = the contract (camelCase JSON)
│   └── predictor.py   load() + predict()  <- the only file you normally edit
├── tests/test_api.py
├── requirements.txt   pinned runtime deps
└── Dockerfile
```

Shared dev tools: `pip install -r requirements-dev.txt` (pytest, httpx, ruff). Lint with `ruff check .` and `ruff format .` (config in `ruff.toml`).
