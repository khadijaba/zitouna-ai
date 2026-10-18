import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import main, predictor
from app.main import app
from app.schemas import YieldRequest

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_parcel_estimate_with_tree_count():
    res = client.post("/predict", json={"governorate": "Sfax", "season": 2026, "treeCount": 200})
    assert res.status_code == 200
    body = res.json()
    assert body["parcelLowKg"] <= body["parcelEstimateKg"] <= body["parcelHighKg"]
    assert body["regionalProductionTonnes"] > 0


def test_regional_only_without_tree_count():
    body = client.post("/predict", json={"governorate": "Sousse", "season": 2025}).json()
    assert body["parcelEstimateKg"] is None


# --- Real model -------------------------------------------------------------------
# A linear model fitted on a synthetic history, exported with the same files as the notebook.

FEATURES = ["lag1_log", "lag2_log", "trend", "rain_sep_may", "rain_jun_aug", "heat_days_apr_may", "tmax_jun_aug"]


@pytest.fixture
def real_model(tmp_path, monkeypatch):
    joblib = pytest.importorskip("joblib")
    from sklearn.linear_model import LinearRegression

    seasons = np.arange(1961, 2025)
    rng = np.random.default_rng(0)
    production = 600_000 * (1 + 0.3 * np.where(seasons % 2 == 0, 1, -1)) * (1 + 0.01 * (seasons - 1961))
    history = pd.DataFrame(
        {
            "production_t": production,
            "area_ha": 1_500_000.0,
            "yield_kg_ha": production * 1000 / 1_500_000,
            "rain_sep_may": rng.uniform(150, 450, len(seasons)),
            "rain_jun_aug": rng.uniform(0, 30, len(seasons)),
            "heat_days_apr_may": rng.uniform(0, 5, len(seasons)),
            "tmax_jun_aug": rng.uniform(31, 36, len(seasons)),
        },
        index=pd.Index(seasons, name="season"),
    )
    # Weather of the next two seasons is known, production is not (like real life after the summer).
    for s in (2025, 2026):
        history.loc[s, ["rain_sep_may", "rain_jun_aug", "heat_days_apr_may", "tmax_jun_aug"]] = [300, 10, 2, 33]
    log_p = np.log(history["production_t"])
    x = pd.DataFrame({"lag1_log": log_p.shift(1), "lag2_log": log_p.shift(2), "trend": history.index - 1961})
    x = x.join(history[FEATURES[3:]]).dropna().loc[:2024]  # seasons with a known production only
    regressor = LinearRegression().fit(x[FEATURES], log_p.loc[x.index])
    joblib.dump(regressor, tmp_path / "model.joblib")
    history.to_csv(tmp_path / "history.csv")
    meta = {"features": FEATURES, "relative_error_quantiles": {"q10": -0.2, "q90": 0.15}, "national_trees": 100_000_000}
    (tmp_path / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    monkeypatch.setattr(predictor, "MODEL_DIR", tmp_path)
    monkeypatch.setattr(predictor, "MODEL_FILE", tmp_path / "model.joblib")
    model = predictor.load()
    assert model is not None
    return model


def test_published_season_returns_faostat_value(real_model):
    res = predictor.predict(real_model, YieldRequest(governorate="Sfax", season=2020))
    assert res.observed is True and res.mock is False and res.scope == "NATIONAL"
    assert res.regional_production_tonnes == round(real_model.production[2020])
    assert res.parcel_estimate_kg is None


def test_future_season_is_forecast_recursively(real_model):
    res = predictor.predict(real_model, YieldRequest(governorate="Sfax", season=2026, tree_count=250, area_ha=2.5))
    assert res.observed is False and res.regional_production_tonnes > 0
    expected = res.regional_production_tonnes * 1000 / 1_500_000 * 2.5
    assert res.parcel_estimate_kg == pytest.approx(expected, rel=1e-3)
    assert res.kg_per_tree == pytest.approx(expected / 250, abs=0.1)
    assert res.parcel_low_kg < res.parcel_estimate_kg < res.parcel_high_kg
    # Season without weather yet: climatology, still a number.
    assert predictor.predict(real_model, YieldRequest(governorate="Sfax", season=2028)).regional_production_tonnes > 0


def test_tree_count_without_area_uses_national_density(real_model):
    res = predictor.predict(real_model, YieldRequest(governorate="Sfax", season=2020, tree_count=100))
    assert res.kg_per_tree == pytest.approx(real_model.production[2020] * 1000 / 100_000_000, abs=0.1)


def test_real_model_through_http(real_model, monkeypatch):
    monkeypatch.setattr(main, "model", real_model)
    body = client.post("/predict", json={"governorate": "Sfax", "season": 2026, "treeCount": 250, "areaHa": 2.5}).json()
    assert body["mock"] is False and body["scope"] == "NATIONAL" and body["observed"] is False
    assert client.post("/predict", json={"governorate": "Sfax", "season": 1950}).status_code == 422
    assert client.get("/health").json()["modelLoaded"] is True
