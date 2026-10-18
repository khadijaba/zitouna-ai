# M5 · Derja assistant (intent detection)

**Owner:** Membre 5 · **Type:** NLP — TF-IDF + SetFit (`multilingual-e5-base`) ensemble, clarification rules, governorate entity.

Detects the intent of a farmer's question written in Tunisian Arabic (Arabic script or arabizi) or mixed with French. The Spring backend (`ChatService`) then routes it to the right module. No business logic, no database here.

| | |
|---|---|
| Endpoints | `POST /intent` `{"text": "..."}` · `POST /answer` (LLM) · `GET /health` |
| Contract | [docs/api-contract.md](../../docs/api-contract.md) (section M5) |
| Port (local / compose) | `8005` |
| Model | `models/m5_ensemble/`, not in Git. Trained by [`notebooks/m5_assistant/train_m5.ipynb`](../../notebooks/m5_assistant/): TF-IDF characters + logistic regression alone (`config.json` + `tfidf.joblib`, `weight_setfit = 0`, a few MB). The TF-IDF + SetFit ensemble (`setfit/`, ~1 GB) is still supported. |

## How it works

```
text ─┬─ normalize()    → TF-IDF pipeline  → p_tfidf  (columns reordered to config.labels)
      └─ light_clean()  → SetFit ("query: ") → p_setfit
p = 0.4 · p_setfit + 0.6 · p_tfidf                     (weight_setfit in config.json)
→ top1, top2, confidence, margin → clarification rules → governorate entity
```

| File | What |
|---|---|
| `app/preprocessing.py` | `normalize` / `light_clean`: **identical to training, do not change** |
| `app/rules.py` | domain words, confusable pairs, clarification questions (Arabic script): edit freely |
| `app/entities.py` | the 24 governorates (Latin, arabizi, Arabic): add spellings freely |
| `app/predictor.py` | loads the ensemble, combines the models; keyword fallback if no model |
| `app/main.py` | FastAPI: models loaded once at startup (lifespan), logs with duration |

Clarification rules, first match wins:
1. **Domain guard:** the top intent is `hors_sujet` but the text mentions olives or farming. This guard exists because refusing a real farmer's question is the worst error.
2. **Disagreement:** the two models disagree and `confidence < clarify_threshold`. With the TF-IDF model alone there is no second opinion: a confidence below `clarify_threshold` (0.35) triggers the question.
3. **Confusable pair:** the top two intents are a known pair and `margin < 0.15`.

## LLM answers (`POST /answer`)

The backend sends the question plus the **facts** computed by the other modules (M2 irrigation, M3 harvest, M4 price, last M1 diagnosis…). An LLM turns them into a short answer in Tunisian derja, **always in Arabic script** (the question may be in arabizi, Arabic or French). It may not invent figures (see the rules in `app/prompt.py`). An answer that is not mostly Arabic script (`is_arabic_script`, ≥ 60 % Arabic letters) is rejected and the next model is tried.

| File | What |
|---|---|
| `app/llm.py` | providers and rotation order (`DEFAULT_CHAIN`), cooldown after 429/503/timeout, truncated answers rejected |
| `app/prompt.py` | rules + 3 example answers: **the place to improve the derja style** |

- Keys go in the root `.env` (`GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`), never in Git. A provider without a key is skipped.
- Free tiers are small: `gemini-3.5-flash` answers ~6 requests per minute before a 429, after which the next model takes over. Adding a free Groq key makes demos much smoother.
- Rotate across **providers or models**, never across several accounts of the same provider (against their terms of service).
- No key, or every model failing: `/answer` returns 503 and the chat uses the template replies. Nothing breaks.
- Live test against the real API: `RUN_LLM_TESTS=1 python -m pytest tests/test_llm.py -k live -s`.

## Run locally

```bash
cd ai-services/m5-assistant
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r ../requirements-dev.txt   # torch CPU, ~1 GB download
uvicorn app.main:app --port 8005   # health: http://localhost:8005/health
python -m pytest -s                # -s prints the probe-set errors
```

Environment variables: `MODEL_DIR` (default `../../models/m5_ensemble`), `PORT` (Docker, default 8000), `MODEL_VERSION`.

`scikit-learn` is pinned to the `sklearn_version` of `config.json` (1.6.1): with another version `joblib.load` may fail. Retrain → update both.

## Tests

- `tests/test_rules.py`: preprocessing, rules, entities and ensemble maths, with fake models (always run, also in CI).
- `tests/test_api.py`: API schema and validation (with the model, or the keyword fallback).
- `tests/test_model.py`: known examples and the probe set `tests/data/m5_probe_set.csv` (≥ 21/25). **Skipped when the model is missing**, e.g. in CI.
