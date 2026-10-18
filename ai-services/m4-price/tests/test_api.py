import csv
import json
import math
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import main, predictor
from app.main import app
from app.schemas import PriceRequest

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_forecast_horizon_and_recommendation():
    res = client.post("/predict", json={"horizonWeeks": 6, "quantityKg": 500})
    assert res.status_code == 200
    body = res.json()
    assert len(body["forecast"]) == 6
    assert body["recommendation"] in {"SELL_NOW", "STORE"}
    assert body["currency"] == "TND"
    assert all(p["low"] <= p["price"] <= p["high"] for p in body["forecast"])


def test_defaults_without_body_fields():
    assert len(client.post("/predict", json={}).json()["forecast"]) == 8


# --- Real model -------------------------------------------------------------------
# A synthetic monthly series + a simple SARIMA order, exported like the notebook does.


def _model_dir(tmp_path, trend_per_month: float, months: int = 120):
    start = date(2015, 1, 1)
    with (tmp_path / "prices.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "price_tnd_kg"])
        for k in range(months):
            d = date(start.year + (start.month - 1 + k) // 12, (start.month - 1 + k) % 12 + 1, 1)
            price = 10 * math.exp(trend_per_month * k) * (1 + 0.03 * math.sin(k / 2.0))
            writer.writerow([d.isoformat(), round(price, 4)])
    config = {"type": "sarima", "order": [1, 1, 0], "seasonal_order": [0, 0, 0, 12], "interval": 0.8, "source": "test"}
    (tmp_path / "model.json").write_text(json.dumps(config), encoding="utf-8")
    return tmp_path


@pytest.fixture
def load_from(monkeypatch):
    def _load(directory):
        monkeypatch.setattr(predictor, "MODEL_FILE", directory / "model.json")
        monkeypatch.setattr(predictor, "PRICES_FILE", directory / "prices.csv")
        model = predictor.load()
        assert model is not None
        return model

    return _load


def test_real_model_contract(tmp_path, load_from):
    model = load_from(_model_dir(tmp_path, 0.0))
    res = predictor.predict(model, PriceRequest(horizon_weeks=12, quantity_kg=1000))
    assert res.mock is False and res.model_version != "mock" and res.source == "test"
    assert len(res.forecast) == 12 and len(res.history) == predictor.HISTORY_MONTHS
    today = predictor._today()
    assert [p.date for p in res.forecast] == [today + timedelta(weeks=w) for w in range(1, 13)]
    assert all(p.low <= p.price <= p.high for p in res.forecast)
    assert all(p.date.day == 15 for p in res.history)
    # The interval widens with the horizon.
    assert res.forecast[-1].high - res.forecast[-1].low >= res.forecast[0].high - res.forecast[0].low


def test_rising_prices_give_store_and_gain(tmp_path, load_from):
    model = load_from(_model_dir(tmp_path, 0.03))  # +3 % per month, far above the storage cost
    res = predictor.predict(model, PriceRequest(horizon_weeks=26, quantity_kg=1000))
    assert res.recommendation == "STORE"
    assert res.expected_gain_tnd and res.expected_gain_tnd > 0
    assert "estimé aujourd'hui" in res.reason


def test_falling_prices_give_sell_now(tmp_path, load_from):
    model = load_from(_model_dir(tmp_path, -0.03))
    res = predictor.predict(model, PriceRequest(horizon_weeks=26, quantity_kg=1000))
    assert res.recommendation == "SELL_NOW" and res.expected_gain_tnd is None


def test_real_model_through_http_endpoint(tmp_path, load_from, monkeypatch):
    monkeypatch.setattr(main, "model", load_from(_model_dir(tmp_path, 0.0)))
    body = client.post("/predict", json={"horizonWeeks": 4}).json()
    assert body["mock"] is False and len(body["forecast"]) == 4 and body["source"] == "test"
    assert client.get("/health").json()["modelLoaded"] is True


def test_interpolation_between_knots():
    knots = [(date(2026, 1, 15), 0.0, -1.0, 1.0), (date(2026, 2, 14), 3.0, 2.0, 4.0)]
    assert predictor._interpolate(knots, date(2026, 1, 30)) == pytest.approx((1.5, 0.5, 2.5))
    assert predictor._interpolate(knots, date(2025, 12, 1)) == (0.0, -1.0, 1.0)
    assert predictor._interpolate(knots, date(2026, 6, 1)) == (3.0, 2.0, 4.0)


def test_prudence_margin_blocks_small_gains(tmp_path, load_from):
    directory = _model_dir(tmp_path, 0.02)  # +2 % per month: about +12 % in 6 months
    config = json.loads((directory / "model.json").read_text(encoding="utf-8"))
    model = load_from(directory)
    assert predictor.predict(model, PriceRequest(horizon_weeks=26)).recommendation == "STORE"

    config["min_gain_share"] = 0.5  # store only if +50 % after storage: never here
    (directory / "model.json").write_text(json.dumps(config), encoding="utf-8")
    res = predictor.predict(load_from(directory), PriceRequest(horizon_weeks=26, quantity_kg=100))
    assert res.recommendation == "SELL_NOW" and res.expected_gain_tnd is None
