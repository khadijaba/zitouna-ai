"""Model loading and inference for M4. This is the file the module owner edits.

Real model (produced by notebooks/m4_price/train_m4.ipynb, exported into models/m4/):

- model.json     SARIMA order chosen on the training data (log price), interval level, data source
- prices.csv     monthly olive-oil price series, TND per kg (date, price_tnd_kg)
- metadata.json  test metrics (MAPE, simulated gain of the advice), versions (information)

At start-up the SARIMA order is re-fitted on the whole series (about one second). For each request:
monthly forecast with an 80 % interval -> linear interpolation of the log price to today (estimated
current price) and to each requested week -> sell / store rule (forecast price minus storage cost).

Without models/m4/model.json the service answers with a synthetic curve and mock=True.
"""

from __future__ import annotations

import csv
import json
import logging
import math
import os
import warnings
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from itertools import pairwise
from pathlib import Path

from app.schemas import Point, PriceRequest, PriceResponse

logger = logging.getLogger(__name__)

MODEL_DIR = Path(os.getenv("MODEL_DIR", "../../models/m4"))
MODEL_FILE = MODEL_DIR / "model.json"
PRICES_FILE = MODEL_DIR / "prices.csv"
MODEL_VERSION = os.getenv("MODEL_VERSION", "sarima")

STORAGE_COST_TND_PER_KG_MONTH = 0.15
HISTORY_WEEKS = 26  # mock mode
HISTORY_MONTHS = 24  # real mode: last observed monthly prices sent to the app
TUNIS_TZ = timezone(timedelta(hours=1))


@dataclass
class LoadedModel:
    """Fitted SARIMA + the observed series (month start dates, TND/kg)."""

    results: object  # statsmodels SARIMAXResults on the log price
    dates: list[date]
    prices: list[float]
    interval: float
    source: str
    min_gain_share: float = 0.0  # prudence margin chosen on the validation years (share of today's price)


def load() -> LoadedModel | None:
    """Return the fitted model, or None to run in mock mode."""
    if not MODEL_FILE.exists() or not PRICES_FILE.exists():
        return None
    try:
        config = json.loads(MODEL_FILE.read_text(encoding="utf-8"))
        dates, prices = _read_prices(PRICES_FILE)
        results = _fit_sarima(prices, dates, tuple(config["order"]), tuple(config["seasonal_order"]))
        logger.info("M4 SARIMA%s%s fitted on %d months", config["order"], config["seasonal_order"], len(prices))
        return LoadedModel(
            results,
            dates,
            prices,
            interval=float(config.get("interval", 0.8)),
            source=config.get("source", ""),
            min_gain_share=float(config.get("min_gain_share", 0.0)),
        )
    except Exception:
        logger.exception("Could not load the M4 model: mock mode")
        return None


def _read_prices(path: Path) -> tuple[list[date], list[float]]:
    dates, prices = [], []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            dates.append(date.fromisoformat(row["date"][:10]))
            prices.append(float(row["price_tnd_kg"]))
    return dates, prices


def _fit_sarima(prices: list[float], dates: list[date], order: tuple, seasonal: tuple):
    import numpy as np
    import pandas as pd
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    series = pd.Series(np.log(prices), index=pd.DatetimeIndex(dates, freq="MS"))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return SARIMAX(series, order=order, seasonal_order=seasonal).fit(disp=False)


def predict(model: LoadedModel | None, req: PriceRequest) -> PriceResponse:
    today = _today()
    if model is None:
        history, forecast = _mock_series(req.horizon_weeks)
        current = history[-1].price
    else:
        history, forecast, current = _model_series(model, req.horizon_weeks, today)

    # Same rule as the notebook: the week that maximises (price - storage cost), against today's price,
    # with the prudence margin learnt on the validation years.
    def net_gain(p: Point) -> float:
        return p.price - current - STORAGE_COST_TND_PER_KG_MONTH * (p.date - today).days / 30

    best = max(forecast, key=net_gain)
    net_gain_per_kg = net_gain(best)
    margin = 0.0 if model is None else model.min_gain_share * current
    now_label = "prix actuel" if model is None else "prix estimé aujourd'hui"

    if net_gain_per_kg > margin:
        recommendation = "STORE"
        reason = (
            f"Le prix pourrait atteindre {best.price:.2f} TND/kg vers le {best.date:%d/%m}, "
            f"soit +{net_gain_per_kg:.2f} TND/kg après coût de stockage ({now_label} : {current:.2f} TND/kg)."
        )
    else:
        recommendation = "SELL_NOW"
        reason = f"Aucune hausse nette attendue au-delà du coût de stockage : {now_label} {current:.2f} TND/kg."

    gain = round(net_gain_per_kg * req.quantity_kg, 2) if req.quantity_kg and recommendation == "STORE" else None
    return PriceResponse(
        history=history,
        forecast=forecast,
        recommendation=recommendation,
        reason=reason,
        expected_gain_tnd=gain,
        model_version="mock" if model is None else MODEL_VERSION,
        mock=model is None,
        source=None if model is None else model.source,
    )


def _model_series(model: LoadedModel, horizon_weeks: int, today: date) -> tuple[list[Point], list[Point], float]:
    """Monthly SARIMA forecast, interpolated to today and to each week. Prices of month M are dated M-15."""
    last = model.dates[-1]
    target = today + timedelta(weeks=horizon_weeks)
    steps = max(1, _months_between(last, target) + 1)
    fc = model.results.get_forecast(steps)
    mean = [float(v) for v in fc.predicted_mean]
    ci = [[float(a), float(b)] for a, b in fc.conf_int(alpha=1 - model.interval).to_numpy()]

    # Knots for the interpolation: the last observed month, then the forecast months.
    last_log = math.log(model.prices[-1])
    knots = [(_mid_month(last), last_log, last_log, last_log)]
    for k in range(steps):
        knots.append((_mid_month(_add_months(last, k + 1)), mean[k], ci[k][0], ci[k][1]))

    current = round(math.exp(_interpolate(knots, today)[0]), 2)
    forecast = []
    for w in range(1, horizon_weeks + 1):
        d = today + timedelta(weeks=w)
        m, lo, hi = _interpolate(knots, d)
        price = math.exp(m)
        forecast.append(
            Point(
                date=d,
                price=round(price, 2),
                low=round(min(math.exp(lo), price), 2),
                high=round(max(math.exp(hi), price), 2),
            )
        )
    history = [
        Point(date=_mid_month(d), price=round(p, 2))
        for d, p in zip(model.dates[-HISTORY_MONTHS:], model.prices[-HISTORY_MONTHS:], strict=True)
    ]
    return history, forecast, current


def _interpolate(knots: list[tuple], day: date) -> tuple[float, float, float]:
    """Linear interpolation of (mean, low, high) between the knots surrounding `day` (clamped at the ends)."""
    if day <= knots[0][0]:
        return knots[0][1:]
    for (d0, *v0), (d1, *v1) in pairwise(knots):
        if d0 <= day <= d1:
            share = (day - d0).days / max((d1 - d0).days, 1)
            return tuple(a + share * (b - a) for a, b in zip(v0, v1, strict=True))
    return knots[-1][1:]


def _months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


def _add_months(d: date, months: int) -> date:
    index = d.year * 12 + d.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def _mid_month(d: date) -> date:
    return date(d.year, d.month, 15)


def _today() -> date:
    """Today in Tunisia (UTC+1 all year)."""
    return datetime.now(TUNIS_TZ).date()


def _mock_series(horizon: int) -> tuple[list[Point], list[Point]]:
    today = _today()

    def price(week: int) -> float:  # gentle seasonal wave around 13 TND/kg
        return 13 + 1.2 * math.sin(week / 8) + 0.3 * math.sin(week * 1.7)

    history = [
        Point(date=today - timedelta(weeks=HISTORY_WEEKS - 1 - i), price=round(price(i), 2))
        for i in range(HISTORY_WEEKS)
    ]
    forecast = []
    for h in range(1, horizon + 1):
        p = price(HISTORY_WEEKS - 1 + h)
        spread = 0.15 * math.sqrt(h)
        forecast.append(
            Point(
                date=today + timedelta(weeks=h), price=round(p, 2), low=round(p - spread, 2), high=round(p + spread, 2)
            )
        )
    return history, forecast
