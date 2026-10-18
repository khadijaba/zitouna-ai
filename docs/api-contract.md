# API contract

Frozen at the end of week 2. Every change goes through a PR reviewed by the backend owner (M2) and the frontend owner (M4), see [CONTRIBUTING.md](../CONTRIBUTING.md#changing-the-api-contract).

- All JSON uses **camelCase**. Python services keep snake_case internally (Pydantic aliases do the conversion).
- Errors from the backend are [RFC 9457 ProblemDetail](https://www.rfc-editor.org/rfc/rfc9457): `{"status": 404, "title": "Not Found", "detail": "Parcel 3 not found"}`.
- Every AI result has `"mock": true` while the module has no trained model yet. The app shows a "données de démo" badge.

Where the contract lives in code (keep the three in sync):

| Layer | Files |
|---|---|
| AI service (Python) | `ai-services/mX-*/app/schemas.py` |
| Backend (Java) | `backend/src/main/java/tn/zitouna/ai/*/…Result.java`, `…Client.Request` |
| Frontend (TypeScript) | `frontend/src/app/core/api/models.ts` |

---

## 1. Backend API (what the Angular app calls)

Base URL `/api`. All endpoints except `/api/auth/**` need `Authorization: Bearer <token>`. Backend home page (live state + routes): http://localhost:8080

| Method | Path | Body / params | Response | Module |
|---|---|---|---|---|
| POST | `/auth/register` | `{fullName, email, password}` | `201 {token, expiresAt, user}` | — |
| POST | `/auth/login` | `{email, password}` | `{token, expiresAt, user}` | — |
| GET | `/users/me` | | `{id, fullName, email, role}` | — |
| GET | `/status` (public) | | `{application, database, modules[{id, name, type, up, modelLoaded, latencyMs, error}], checkedAt}` | — |
| GET / PATCH / DELETE | `/admin/**` (ADMIN role) | see [backend/README.md](../backend/README.md#admin-back-office) | stats, users, parcels, predictions of every user | — |
| GET | `/parcels` | | `Parcel[]` | — |
| POST | `/parcels` | `ParcelRequest` | `201 Parcel` | — |
| GET / PUT / DELETE | `/parcels/{id}` | `ParcelRequest` for PUT | `Parcel` / `204` | — |
| POST | `/ai/disease` | multipart `image`, optional `?parcelId=` | `DiseaseResult` | M1 |
| GET | `/parcels/{id}/irrigation` | optional `?days=7` (1–16) | `IrrigationResult` | M2 |
| GET | `/parcels/{id}/yield` | optional `?season=2026` | `YieldResult` | M3 |
| GET | `/ai/price` | `?horizonWeeks=8&quantityKg=` | `PriceResult` | M4 |
| POST | `/ai/chat` | `{text, parcelId?, forcedIntent?}` | `{reply, intent, clarify, suggestions, data, mock, generatedBy}` | M5 → M1…M6 / RAG → LLM |
| POST | `/parcels/{id}/count-trees` | multipart `image` | `TreeCountResult` (also saves `treeCount` on the parcel when not mock) | M6 |
| POST | `/parcels/{id}/harvest-plan` | optional multipart `image` | `HarvestPlan` | M6 → M3 → M4 |
| GET | `/history` | `?type=DISEASE&page=0&size=20` | `{content: Prediction[], page, size, totalElements, totalPages}` | — |

`Parcel`:

```json
{ "id": 1, "name": "Henchir Sfax", "governorate": "Sfax", "latitude": 34.74, "longitude": 10.76,
  "areaHa": 2.5, "treeCount": 250, "variety": "Chemlali", "irrigated": false, "createdAt": "2026-10-07T10:00:00Z" }
```

`ParcelRequest` is the same without `id` and `createdAt`. `name`, `governorate`, `latitude`, `longitude` are required.

`HarvestPlan`:

```json
{ "treeCount": 250, "treeCountSource": "M6", "yield": { "…": "YieldResult" }, "estimatedOilKg": 1500.0,
  "price": { "…": "PriceResult" }, "summary": "250 arbres, récolte estimée 7500 kg d'olives (≈ 1500 kg d'huile). Conseil : stocker.",
  "mock": true }
```

---

## 2. AI services (what the backend calls)

Each service is a FastAPI app on port `8000` in Docker (`8001`–`8006` on your machine). Each exposes:

- `GET /health` → `{"status": "ok", "module": "m1-disease", "modelLoaded": false}`
- `POST /predict` → described below. Invalid input → `422`.

### M1

`POST /predict` — multipart field `image` (JPEG/PNG of one leaf).

```json
{
  "label": "peacock_spot",
  "labelFr": "Œil de paon",
  "confidence": 0.82,
  "probabilities": { "healthy": 0.06, "peacock_spot": 0.82, "aculus_olearius": 0.06, "olive_knot": 0.06 },
  "advice": "Traitement préventif à base de cuivre…",
  "heatmapBase64": null,
  "modelVersion": "mock",
  "mock": true
}
```

`label` ∈ `healthy | peacock_spot | aculus_olearius | olive_knot`. `heatmapBase64`: optional Grad-CAM PNG.

### M2

`POST /predict`

```json
{ "latitude": 34.74, "longitude": 10.76, "treeCount": 250, "areaHa": 2.5, "days": 7 }
```

```json
{
  "days": [
    { "date": "2026-10-07", "et0Mm": 4.1, "rainMm": 0.0, "waterNeedMm": 2.67, "litersPerTree": 266.5, "irrigate": true }
  ],
  "alerts": [
    { "date": "2026-10-09", "type": "HEATWAVE", "severity": "MEDIUM", "message": "Canicule (41 °C) : irriguez tôt le matin ou le soir." }
  ],
  "modelVersion": "mock",
  "mock": true
}
```

`waterNeedMm = ET0 × Kc − 0.8 × rain` (Kc olive = 0.65, FAO-56). `litersPerTree` is `null` without `treeCount` and `areaHa`. `type` ∈ `FROST | HEATWAVE`, `severity` ∈ `LOW | MEDIUM | HIGH`.

With the trained model: `et0Mm` comes from the LSTM (fed with the last 30 days of Open-Meteo weather), `rainMm` and the alert temperatures from the Open-Meteo forecast. The first day is today (Tunisia time). If Open-Meteo cannot be reached, the service answers with synthetic weather and `mock: true`.

### M3

`POST /predict`

```json
{ "governorate": "Sfax", "season": 2026, "treeCount": 250, "areaHa": 2.5 }
```

```json
{
  "governorate": "Sfax", "season": 2026, "regionalProductionTonnes": 1250000,
  "kgPerTree": 6.7, "parcelEstimateKg": 1675, "parcelLowKg": 795, "parcelHighKg": 3180,
  "modelVersion": "m3-national", "mock": false, "scope": "NATIONAL", "observed": false
}
```

`season` = year the harvest starts (2026 = 2026/2027). Parcel fields are `null` without `treeCount` and `areaHa`.
Additive fields: `scope` = `NATIONAL` with the trained model (`regionalProductionTonnes` is then the production of
**Tunisia**: open regional data does not exist, roadmap plan B), `REGIONAL` in mock mode; `observed` = the season is
already published by FAOSTAT (the real figure, not a forecast). The parcel estimate uses `areaHa` (national yield per
ha) or, without area, `treeCount` (national production / ~100 million trees).

### M4

`POST /predict`

```json
{ "horizonWeeks": 8, "quantityKg": 1500 }
```

```json
{
  "currency": "TND", "unit": "kg",
  "history":  [ { "date": "2026-04-15", "price": 12.4, "low": null, "high": null } ],
  "forecast": [ { "date": "2026-10-14", "price": 13.1, "low": 12.95, "high": 13.25 } ],
  "recommendation": "STORE",
  "reason": "Le prix pourrait atteindre 13.60 TND/kg vers le 25/11, soit +0.42 TND/kg après coût de stockage.",
  "expectedGainTnd": 630.0,
  "modelVersion": "mock", "mock": true
}
```

Prices are olive-oil prices in TND per kg of oil. `recommendation` ∈ `SELL_NOW | STORE`. `expectedGainTnd` is `null` without `quantityKg` or when selling now is better.

With the trained model: `history` = the last 24 **monthly** observed prices (dated the 15th), `forecast` = one point per week from today (monthly SARIMA forecast interpolated, `low` / `high` = 80 % interval). Additive field `source` (string, `null` in mock mode): where the prices come from — the IMF world price converted to TND until the team types in the COI Tunisian producer prices (see `notebooks/m4_price/README.md`).

### M5

`POST /intent` (M5 only exposes `/intent` instead of `/predict`) — `text`: 1 to 500 characters, Arabic script, arabizi or French/derja mix.

```json
{ "text": "fama jlid ghodwa fi beja?" }
```

```json
{
  "intent": "meteo_alerte", "confidence": 0.91, "clarify": false, "question": null,
  "candidates": [ { "intent": "meteo_alerte", "score": 0.91 }, { "intent": "irrigation", "score": 0.04 },
                  { "intent": "conseil_general", "score": 0.02 } ],
  "modelsAgree": true,
  "entities": { "gouvernorat": "beja" },
  "modelVersion": "m5_ensemble", "mock": false
}
```

- `intent` ∈ `maladie | irrigation | meteo_alerte | recolte | prix_vente | comptage | conseil_general | salutation | hors_sujet`. When `clarify` is `true`, `intent` is still the best guess and `question` is the question to ask the farmer (derja, arabizi).
- `candidates`: top 3, best first. `modelsAgree`: TF-IDF and SetFit have the same top intent.
- `entities.gouvernorat`: canonical id of the governorate cited (`"sfax"`, `"sidi bouzid"`…), or `null`.
- `mock: true` = keyword fallback (the trained ensemble is not in `MODEL_DIR`).

Routing, done by the backend (`ChatService`): `maladie` → M1, `irrigation` / `meteo_alerte` → M2, `recolte` → M3, `prix_vente` → M4, `comptage` → M6, `conseil_general` → RAG, `salutation` / `hors_sujet` → fixed reply. If M5 is down or slower than 3 s, the backend answers with the generic clarification question.

Backend `POST /api/ai/chat` response:

```json
{
  "reply": "ما فماش حتى تنبيه متاع جليد في باجة السبعة أيام الجايين، وفما شوية شتا نهار 12 أكتوبر. (معطيات تجريبية)",
  "intent": "meteo_alerte", "clarify": false, "suggestions": [], "data": [ { "…": "Alert" } ], "mock": true,
  "generatedBy": "gemini/gemini-2.5-flash"
}
```

With `clarify: true`, `reply` is the question and `suggestions` the intents to show as buttons; clicking one resends the same `text` with `forcedIntent`. `generatedBy` is `"template"` when no LLM wrote the reply. Every `reply` (LLM or template) is Tunisian derja in **Arabic script**, whatever the script of the question (arabizi, Arabic, French).

`POST /answer` — the LLM writes the reply from the facts gathered by the backend (rotation across free APIs, see `app/llm.py`). `503` when no LLM is configured or all fail: the backend then uses its template reply.

```json
{
  "question": "9adech bech njib zit had el 3am?", "intent": "recolte",
  "facts": [ { "source": "M3", "mock": true, "data": { "estimation_parcelle_kg_olives": 7500 } },
             { "source": "M4", "mock": true, "data": { "prix_huile_aujourdhui_tnd_kg": 12.72, "conseil": "STORE" } } ],
  "parcel": { "name": "Henchir Sfax", "governorate": "Sfax", "treeCount": 250, "areaHa": 2.5 },
  "draft": "صابة صفاقس (موسم 2026/2027) ≈ 504000 طن زيتون. …"
}
```

```json
{ "answer": "للقطعة متاعك نقدرو 7500 كغ زيتون… (معطيات تجريبية)", "provider": "gemini", "model": "gemini-3.5-flash", "latencyMs": 1420 }
```

Facts per intent (backend `ChatService.ENRICH`): `meteo_alerte` = M2 alerts + irrigation plan, `recolte` = M3 + M4, `prix_vente` = M4 + M3, `maladie` = latest M1 diagnosis from the history. Only facts and the parcel profile are sent to the LLM, never personal data.

### M6

`POST /predict` — multipart field `image` (drone or satellite view of a parcel).

```json
{
  "treeCount": 42,
  "boxes": [ { "x": 120.0, "y": 64.0, "width": 30.0, "height": 30.0, "confidence": 0.91 } ],
  "annotatedImageBase64": "iVBORw0KGgo…",
  "modelVersion": "mock", "mock": true
}
```

Box coordinates are in pixels of the (possibly downscaled, max 1280 px) image.
