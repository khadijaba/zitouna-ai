"""Model loading and inference for M2. This is the file the module owner edits.

Real model (produced by notebooks/m2_irrigation/train_m2.ipynb, exported into models/m2/):

- lstm_et0.npz   LSTM weights + normalisation: 30 days of weather -> ET0 of the next 16 days
- metadata.json  metrics, data period, versions (information)

Inference chain:
1. Open-Meteo forecast API for the parcel (no key): the last 30 days (inputs of the LSTM) and the
   coming days (rain, Tmin, Tmax from the numerical weather forecast).
2. LSTM (NumPy forward pass, same computation as PyTorch) -> ET0 for each coming day.
3. FAO-56 water balance: need = ET0 x Kc - 0.8 x rain, litres per tree, frost / heatwave alerts.

Without models/m2/lstm_et0.npz, or when Open-Meteo is unreachable, the service answers with synthetic
weather and mock=True, so the backend and the app keep working.
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from app.schemas import Alert, Day, IrrigationRequest, IrrigationResponse

logger = logging.getLogger(__name__)

MODEL_DIR = Path(os.getenv("MODEL_DIR", "../../models/m2"))
MODEL_FILE = MODEL_DIR / "lstm_et0.npz"
MODEL_VERSION = os.getenv("MODEL_VERSION", "lstm-et0")
FORECAST_URL = os.getenv("OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast")
if not FORECAST_URL.startswith("https://"):  # urlopen also accepts file:// and other schemes
    raise ValueError("OPEN_METEO_URL must be an https:// URL")
WEATHER_TIMEOUT_S = float(os.getenv("M2_WEATHER_TIMEOUT", "8"))
CACHE_TTL_S = 3600

KC_OLIVE = 0.65  # FAO-56 crop coefficient, mature olive grove
EFFECTIVE_RAIN = 0.8  # share of rain that reaches the roots
IRRIGATE_THRESHOLD_MM = 2.0
FROST_C, HEATWAVE_C = 0.0, 40.0

DAILY_VARS = ["et0_fao_evapotranspiration", "precipitation_sum", "temperature_2m_max", "temperature_2m_min"]

TUNIS_TZ = timezone(timedelta(hours=1))
_cache: dict[tuple, tuple[float, dict]] = {}


class WeatherUnavailable(RuntimeError):
    pass


def load() -> dict | None:
    """Return the trained LSTM (dict of arrays), or None to run in mock mode."""
    if not MODEL_FILE.exists():
        return None
    try:
        with np.load(MODEL_FILE) as archive:
            weights = {k: archive[k].astype(np.float64) for k in archive.files}
        weights["window"] = int(weights["window"])
        weights["horizon"] = int(weights["horizon"])
        logger.info("M2 model loaded: window=%d, horizon=%d", weights["window"], weights["horizon"])
        return weights
    except Exception:
        logger.exception("Could not load %s: mock mode", MODEL_FILE)
        return None


def predict(model: dict | None, req: IrrigationRequest) -> IrrigationResponse:
    forecast = None
    if model is not None:
        try:
            forecast = _model_forecast(model, req)
        except WeatherUnavailable as e:
            logger.warning("Open-Meteo unavailable (%s): synthetic weather, mock=true", e)
    mock = forecast is None
    if mock:
        forecast = _mock_forecast(req)

    days, alerts = [], []
    for d, et0, rain, tmin, tmax in forecast:
        need = max(0.0, et0 * KC_OLIVE - EFFECTIVE_RAIN * rain)
        days.append(
            Day(
                date=d,
                et0_mm=round(et0, 2),
                rain_mm=round(rain, 1),
                water_need_mm=round(need, 2),
                liters_per_tree=_liters_per_tree(need, req),
                irrigate=need >= IRRIGATE_THRESHOLD_MM,
            )
        )
        if tmin <= FROST_C:
            alerts.append(
                Alert(
                    date=d,
                    type="FROST",
                    severity="HIGH" if tmin <= -2 else "MEDIUM",
                    message=f"Risque de gel ({tmin:.0f} °C) : protégez les jeunes plants.",
                )
            )
        if tmax >= HEATWAVE_C:
            alerts.append(
                Alert(
                    date=d,
                    type="HEATWAVE",
                    severity="HIGH" if tmax >= 44 else "MEDIUM",
                    message=f"Canicule ({tmax:.0f} °C) : irriguez tôt le matin ou le soir.",
                )
            )

    return IrrigationResponse(days=days, alerts=alerts, model_version="mock" if mock else MODEL_VERSION, mock=mock)


def _model_forecast(model: dict, req: IrrigationRequest) -> list[tuple]:
    """[(date, et0, rain, tmin, tmax)] for today .. today + days - 1: ET0 from the LSTM, the rest from Open-Meteo."""
    window = model["window"]
    weather = fetch_weather(req.latitude, req.longitude, past_days=window, forecast_days=req.days)
    times = [date.fromisoformat(t) for t in weather["time"]]
    today = _today()
    if today not in times:
        raise WeatherUnavailable("today missing from the Open-Meteo answer")
    t0 = times.index(today)
    if t0 < window:
        raise WeatherUnavailable("not enough past days")

    et0_col, rain_col = weather["et0_fao_evapotranspiration"], weather["precipitation_sum"]
    tmax_col, tmin_col = weather["temperature_2m_max"], weather["temperature_2m_min"]
    past = []
    for k in range(t0 - window, t0):
        if et0_col[k] is None or tmax_col[k] is None or tmin_col[k] is None:
            raise WeatherUnavailable(f"missing past value on {times[k]}")
        angle = 2 * math.pi * times[k].timetuple().tm_yday / 365.25
        past.append([et0_col[k], rain_col[k] or 0.0, tmax_col[k], tmin_col[k], math.sin(angle), math.cos(angle)])
    et0_pred = lstm_forward(model, np.asarray(past, dtype=np.float64))

    out = []
    for h in range(min(req.days, model["horizon"], len(times) - t0)):
        k = t0 + h
        if tmax_col[k] is None or tmin_col[k] is None:
            raise WeatherUnavailable(f"missing forecast on {times[k]}")
        out.append((times[k], float(et0_pred[h]), float(rain_col[k] or 0.0), float(tmin_col[k]), float(tmax_col[k])))
    if len(out) < req.days:
        raise WeatherUnavailable("forecast shorter than requested")
    return out


def lstm_forward(model: dict, past: np.ndarray) -> np.ndarray:
    """past: (window, 6) raw features in the training order -> ET0 (mm/day) of the next `horizon` days."""
    x = (past - model["feat_mean"]) / model["feat_std"]
    w_ih, w_hh = model["w_ih"], model["w_hh"]
    bias = model["b_ih"] + model["b_hh"]
    h = np.zeros(w_hh.shape[1])
    c = np.zeros(w_hh.shape[1])
    for t in range(x.shape[0]):
        gates = w_ih @ x[t] + w_hh @ h + bias
        i, f, g, o = np.split(gates, 4)  # PyTorch gate order
        c = _sigmoid(f) * c + _sigmoid(i) * np.tanh(g)
        h = _sigmoid(o) * np.tanh(c)
    out = model["head_w"] @ h + model["head_b"]
    return np.clip(out * model["et0_std"] + model["et0_mean"], 0.0, None)


def _sigmoid(v: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-v))


def fetch_weather(latitude: float, longitude: float, past_days: int, forecast_days: int) -> dict:
    """Open-Meteo daily forecast + recent past for a point; cached 1 h per ~10 km cell."""
    key = (round(latitude, 1), round(longitude, 1), past_days, forecast_days, _today())
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_S:
        return hit[1]
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join(DAILY_VARS),
        "past_days": past_days,
        "forecast_days": forecast_days,
        "timezone": "Africa/Tunis",
    }
    url = f"{FORECAST_URL}?{urllib.parse.urlencode(params, safe=',')}"
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            # Scheme restricted to https at import time (see FORECAST_URL).
            with urllib.request.urlopen(url, timeout=WEATHER_TIMEOUT_S) as response:  # nosec B310
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("error") or "daily" not in payload:
                raise WeatherUnavailable(payload.get("reason", "no daily data"))
            _cache[key] = (time.monotonic(), payload["daily"])
            return payload["daily"]
        except Exception as e:  # timeout, DNS, "service overloaded"...
            last_error = e
            time.sleep(0.5 * (attempt + 1))
    raise WeatherUnavailable(str(last_error))


def _liters_per_tree(need_mm: float, req: IrrigationRequest) -> float | None:
    """1 mm of water on 1 m² = 1 litre."""
    if not req.tree_count or not req.area_ha:
        return None
    m2_per_tree = req.area_ha * 10_000 / req.tree_count
    return round(need_mm * m2_per_tree, 1)


def _mock_forecast(req: IrrigationRequest):
    """Synthetic but plausible weather; warmer in the south (lower latitude)."""
    warm = max(0.0, 37 - req.latitude)  # Bizerte ~0, Tataouine ~4
    out = []
    for i in range(req.days):
        d = _today() + timedelta(days=i)
        season = math.sin((d.timetuple().tm_yday - 105) / 365 * 2 * math.pi)  # peak in July
        et0 = 3.5 + 2.5 * season + 0.3 * warm + 0.4 * math.sin(i)
        rain = 6.0 if i % 5 == 3 and season < 0.5 else 0.0
        tmax = 26 + 10 * season + 1.5 * warm + 2 * math.sin(i * 1.3)
        tmin = tmax - 12
        out.append((d, et0, rain, tmin, tmax))
    return out


def _today() -> date:
    """Today in Tunisia (UTC+1 all year, no daylight saving), the timezone of the Open-Meteo answer."""
    return datetime.now(TUNIS_TZ).date()
