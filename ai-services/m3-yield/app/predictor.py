"""Model loading and inference for M3. This is the file the module owner edits.

Real model (produced by notebooks/m3_yield/train_m3.ipynb, exported into models/m3/):

- model.joblib   scikit-learn regressor: features of a season -> log of the national olive production
- history.csv    per season: FAOSTAT production / area / yield + seasonal ERA5 weather (12 governorates)
- metadata.json  features, error quantiles of the rolling test, metrics, versions

Plan B of the roadmap: the forecast is **national** (regional ONAGRI data is not open). For a season already
published by FAOSTAT the observed production is returned (observed=true). Later seasons are forecast one after
the other (the forecast of S-1 feeds the alternate-bearing feature of S); a season whose weather is not complete
yet uses the average weather of the last 10 seasons.

Parcel: national yield per hectare x parcel area; without area, national production / ~100 million trees x tree
count. The interval comes from the real errors of the rolling test (10 % and 90 % quantiles).

Until models/m3/model.joblib exists, the service runs in mock mode with rough regional figures.
"""

from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass
from pathlib import Path

from app.schemas import YieldRequest, YieldResponse

logger = logging.getLogger(__name__)

MODEL_DIR = Path(os.getenv("MODEL_DIR", "../../models/m3"))
MODEL_FILE = MODEL_DIR / "model.joblib"
MODEL_VERSION = os.getenv("MODEL_VERSION", "m3-national")

INTERVAL = 0.25  # mock mode: +/- 25 %
WEATHER_FEATURES = ["rain_sep_may", "rain_jun_aug", "heat_days_apr_may", "tmax_jun_aug"]

# Placeholder orders of magnitude (tonnes of olives), mock mode only.
MOCK_REGIONAL_TONNES = {
    "sfax": 420_000,
    "sidi bouzid": 260_000,
    "kairouan": 190_000,
    "mahdia": 160_000,
    "sousse": 120_000,
    "monastir": 90_000,
    "gafsa": 60_000,
    "kasserine": 55_000,
}
MOCK_KG_PER_TREE = 25.0


@dataclass
class LoadedModel:
    regressor: object
    features: list[str]
    production: dict[int, float]  # FAOSTAT, tonnes
    area: dict[int, float]  # FAOSTAT, hectares
    weather: dict[int, dict[str, float]]  # complete seasons only
    q10: float
    q90: float
    national_trees: float


def load() -> LoadedModel | None:
    """Return the trained model, or None to run in mock mode."""
    if not MODEL_FILE.exists():
        return None
    try:
        import joblib
        import pandas as pd

        meta = json.loads((MODEL_DIR / "metadata.json").read_text(encoding="utf-8"))
        history = pd.read_csv(MODEL_DIR / "history.csv", index_col="season")
        weather = history.dropna(subset=WEATHER_FEATURES)[WEATHER_FEATURES]
        model = LoadedModel(
            regressor=joblib.load(MODEL_FILE),
            features=list(meta["features"]),
            production=history["production_t"].dropna().to_dict(),
            area=history["area_ha"].dropna().to_dict(),
            weather={int(s): row.to_dict() for s, row in weather.iterrows()},
            q10=float(meta["relative_error_quantiles"]["q10"]),
            q90=float(meta["relative_error_quantiles"]["q90"]),
            national_trees=float(meta.get("national_trees", 100_000_000)),
        )
        logger.info("M3 model loaded: FAOSTAT up to %d, weather up to %d", max(model.production), max(model.weather))
        return model
    except Exception:
        logger.exception("Could not load the M3 model: mock mode")
        return None


def predict(model: LoadedModel | None, req: YieldRequest) -> YieldResponse:
    if model is None:
        return _mock_response(req)

    production, observed = national_production(model, req.season)
    area = model.area.get(req.season) or model.area[max(model.area)]
    yield_kg_ha = production * 1000 / area
    if req.area_ha:
        estimate = yield_kg_ha * req.area_ha
        kg_per_tree = estimate / req.tree_count if req.tree_count else None
    elif req.tree_count:
        kg_per_tree = production * 1000 / model.national_trees
        estimate = kg_per_tree * req.tree_count
    else:
        estimate, kg_per_tree = None, None

    return YieldResponse(
        governorate=req.governorate,
        season=req.season,
        regional_production_tonnes=round(production),
        kg_per_tree=None if kg_per_tree is None else round(kg_per_tree, 1),
        parcel_estimate_kg=_round(estimate),
        parcel_low_kg=_round(estimate and estimate * (1 + min(model.q10, 0.0))),
        parcel_high_kg=_round(estimate and estimate * (1 + max(model.q90, 0.0))),
        model_version=MODEL_VERSION,
        mock=False,
        scope="NATIONAL",
        observed=observed,
    )


def national_production(model: LoadedModel, season: int) -> tuple[float, bool]:
    """(tonnes, observed). Seasons after the last FAOSTAT year are forecast recursively."""
    if season in model.production:
        return model.production[season], True
    known = dict(model.production)
    first_unknown = max(known) + 1
    if season < first_unknown:  # before 1961: not covered
        raise ValueError(f"season {season} is outside the FAOSTAT range")
    for s in range(first_unknown, season + 1):
        known[s] = _forecast_one(model, s, known)
    return known[season], False


def _forecast_one(model: LoadedModel, season: int, known: dict[int, float]) -> float:
    weather = model.weather.get(season) or _climatology(model)
    row = {
        "lag1_log": math.log(known[season - 1]),
        "lag2_log": math.log(known[season - 2]),
        "trend": season - 1961,
        **weather,
    }
    import pandas as pd

    x = pd.DataFrame([[row[f] for f in model.features]], columns=model.features)
    return float(math.exp(model.regressor.predict(x)[0]))


def _climatology(model: LoadedModel) -> dict[str, float]:
    last = sorted(model.weather)[-10:]
    return {f: sum(model.weather[s][f] for s in last) / len(last) for f in WEATHER_FEATURES}


def _mock_response(req: YieldRequest) -> YieldResponse:
    alternate = 1.2 if req.season % 2 == 0 else 0.8  # "on" year vs "off" year
    regional = MOCK_REGIONAL_TONNES.get(req.governorate.strip().lower(), 40_000) * alternate
    kg_per_tree = MOCK_KG_PER_TREE * alternate
    estimate = req.tree_count * kg_per_tree if req.tree_count else None
    return YieldResponse(
        governorate=req.governorate,
        season=req.season,
        regional_production_tonnes=round(regional),
        kg_per_tree=round(kg_per_tree, 1),
        parcel_estimate_kg=_round(estimate),
        parcel_low_kg=_round(estimate and estimate * (1 - INTERVAL)),
        parcel_high_kg=_round(estimate and estimate * (1 + INTERVAL)),
        model_version="mock",
        mock=True,
    )


def _round(value: float | None) -> float | None:
    return None if value is None else round(value)
