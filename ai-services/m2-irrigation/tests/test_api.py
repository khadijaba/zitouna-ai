from datetime import timedelta

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import main, predictor
from app.main import app
from app.schemas import IrrigationRequest

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_predict_accepts_camel_case_and_returns_7_days():
    res = client.post("/predict", json={"latitude": 34.74, "longitude": 10.76, "treeCount": 250, "areaHa": 2.5})
    assert res.status_code == 200
    body = res.json()
    assert len(body["days"]) == 7
    assert {"date", "et0Mm", "rainMm", "waterNeedMm", "litersPerTree", "irrigate"} <= body["days"][0].keys()
    assert body["days"][0]["litersPerTree"] is not None
    assert isinstance(body["alerts"], list)


def test_rejects_invalid_latitude():
    assert client.post("/predict", json={"latitude": 120, "longitude": 10}).status_code == 422


# --- Real model -------------------------------------------------------------------
# A small random LSTM with the exported layout + a fake Open-Meteo answer: tests the whole chain
# (inputs, NumPy forward pass, water balance, alerts) without network.

WINDOW, HORIZON, HIDDEN = 30, 16, 8


def _fake_model(tmp_path):
    rng = np.random.default_rng(0)
    arrays = {
        "w_ih": rng.normal(0, 0.3, (4 * HIDDEN, 6)),
        "w_hh": rng.normal(0, 0.3, (4 * HIDDEN, HIDDEN)),
        "b_ih": np.zeros(4 * HIDDEN),
        "b_hh": np.zeros(4 * HIDDEN),
        "head_w": rng.normal(0, 0.3, (HORIZON, HIDDEN)),
        "head_b": np.zeros(HORIZON),
        "feat_mean": np.array([3.5, 1.0, 25.0, 14.0, 0.0, 0.0]),
        "feat_std": np.array([1.8, 4.0, 7.0, 6.0, 0.7, 0.7]),
        "et0_mean": np.float64(3.5),
        "et0_std": np.float64(1.8),
        "window": np.int64(WINDOW),
        "horizon": np.int64(HORIZON),
    }
    np.savez(tmp_path / "lstm_et0.npz", **arrays)
    return tmp_path


def _fake_weather(past_days, forecast_days, tmin_future=12.0, tmax_future=30.0):
    today = predictor._today()
    days = [today + timedelta(days=k) for k in range(-past_days, forecast_days)]
    n_past = past_days
    return {
        "time": [d.isoformat() for d in days],
        "et0_fao_evapotranspiration": [4.0] * len(days),
        "precipitation_sum": [0.0] * n_past + [5.0] + [0.0] * (forecast_days - 1),
        "temperature_2m_max": [30.0] * n_past + [tmax_future] * forecast_days,
        "temperature_2m_min": [15.0] * n_past + [tmin_future] * forecast_days,
    }


@pytest.fixture
def real_model(tmp_path, monkeypatch):
    monkeypatch.setattr(predictor, "MODEL_FILE", _fake_model(tmp_path) / "lstm_et0.npz")
    model = predictor.load()
    assert model is not None and model["window"] == WINDOW
    return model


def test_real_model_uses_lstm_and_forecast_weather(real_model, monkeypatch):
    calls = {}

    def fake_fetch(lat, lon, past_days, forecast_days):
        calls["args"] = (past_days, forecast_days)
        return _fake_weather(past_days, forecast_days)

    monkeypatch.setattr(predictor, "fetch_weather", fake_fetch)
    req = IrrigationRequest(latitude=34.74, longitude=10.76, tree_count=250, area_ha=2.5, days=7)
    res = predictor.predict(real_model, req)

    assert calls["args"] == (WINDOW, 7)
    assert res.mock is False and res.model_version != "mock"
    assert len(res.days) == 7 and res.days[0].date == predictor._today()
    past = np.array([[4.0, 0.0, 30.0, 15.0, 0.0, 0.0]] * WINDOW)
    expected = predictor.lstm_forward(real_model, past)  # same inputs except the calendar features
    assert all(d.et0_mm >= 0 for d in res.days)
    assert res.days[0].rain_mm == 5.0  # rain comes from the Open-Meteo forecast
    first = res.days[0]
    assert first.water_need_mm == round(max(0.0, first.et0_mm * 0.65 - 0.8 * 5.0), 2)
    assert first.liters_per_tree == round(first.water_need_mm * 100, 1)  # 100 m² per tree
    assert expected.shape == (HORIZON,)


def test_frost_and_heatwave_alerts_from_forecast(real_model, monkeypatch):
    monkeypatch.setattr(
        predictor,
        "fetch_weather",
        lambda la, lo, past_days, forecast_days: _fake_weather(past_days, forecast_days, -3, 45),
    )
    res = predictor.predict(real_model, IrrigationRequest(latitude=35.0, longitude=10.0, days=3))
    types = {(a.type, a.severity) for a in res.alerts}
    assert ("FROST", "HIGH") in types and ("HEATWAVE", "HIGH") in types


def test_weather_down_falls_back_to_mock(real_model, monkeypatch):
    def down(*args, **kwargs):
        raise predictor.WeatherUnavailable("offline")

    monkeypatch.setattr(predictor, "fetch_weather", down)
    res = predictor.predict(real_model, IrrigationRequest(latitude=34.74, longitude=10.76))
    assert res.mock is True and len(res.days) == 7


def test_real_model_through_http_endpoint(real_model, monkeypatch):
    monkeypatch.setattr(
        predictor, "fetch_weather", lambda la, lo, past_days, forecast_days: _fake_weather(past_days, forecast_days)
    )
    monkeypatch.setattr(main, "model", real_model)
    body = client.post("/predict", json={"latitude": 34.74, "longitude": 10.76, "days": 10}).json()
    assert body["mock"] is False and len(body["days"]) == 10
    assert client.get("/health").json()["modelLoaded"] is True


def test_lstm_forward_matches_reference_implementation(real_model):
    """Vectorised NumPy LSTM vs a straightforward per-gate implementation."""
    rng = np.random.default_rng(1)
    past = rng.normal([3.5, 1.0, 25.0, 14.0, 0.0, 0.0], [1.0, 2.0, 5.0, 5.0, 0.5, 0.5], (WINDOW, 6))
    m = real_model
    x = (past - m["feat_mean"]) / m["feat_std"]
    h, c = np.zeros(HIDDEN), np.zeros(HIDDEN)
    sig = lambda v: 1 / (1 + np.exp(-v))  # noqa: E731
    for t in range(WINDOW):
        z = m["w_ih"] @ x[t] + m["b_ih"] + m["w_hh"] @ h + m["b_hh"]
        i, f, g, o = (
            sig(z[:HIDDEN]),
            sig(z[HIDDEN : 2 * HIDDEN]),
            np.tanh(z[2 * HIDDEN : 3 * HIDDEN]),
            sig(z[3 * HIDDEN :]),
        )
        c = f * c + i * g
        h = o * np.tanh(c)
    ref = np.clip((m["head_w"] @ h + m["head_b"]) * m["et0_std"] + m["et0_mean"], 0, None)
    assert np.allclose(predictor.lstm_forward(m, past), ref)
