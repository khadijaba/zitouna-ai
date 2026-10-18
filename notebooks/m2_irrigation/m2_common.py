"""M2 · Irrigation — shared code for the notebook (train_m2.ipynb).

Pipeline: Open-Meteo ERA5 daily weather for the main olive governorates -> chronological split
-> baselines ("same day last year", persistence) -> Prophet -> LSTM -> evaluation (MAE / RMSE
on the forecast ET0, horizons 1–7 days) -> export of the LSTM weights for the FastAPI service.

The service (ai-services/m2-irrigation/app/predictor.py) re-implements the LSTM forward pass in
NumPy: keep FEATURES, WINDOW and HORIZON identical in both files.
"""

from __future__ import annotations

import json
import logging
import math
import random
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "m2_irrigation"
MODEL_DIR = ROOT / "models" / "m2"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

SEED = 42
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_VARS = ["et0_fao_evapotranspiration", "precipitation_sum", "temperature_2m_max", "temperature_2m_min"]
COLUMNS = {
    "et0_fao_evapotranspiration": "et0",
    "precipitation_sum": "rain",
    "temperature_2m_max": "tmax",
    "temperature_2m_min": "tmin",
}

# Main olive-growing governorates (capital coordinates, same as the backend Governorates.java).
REGIONS = {
    "sfax": (34.74, 10.76),
    "sousse": (35.83, 10.64),
    "monastir": (35.78, 10.83),
    "mahdia": (35.50, 11.06),
    "kairouan": (35.68, 10.10),
    "sidi_bouzid": (35.04, 9.48),
    "gabes": (33.88, 10.10),
    "medenine": (33.35, 10.50),
    "nabeul": (36.45, 10.73),
    "zaghouan": (36.40, 10.14),
    "beja": (36.73, 9.18),
    "kasserine": (35.17, 8.83),
}

# Chronological split, never shuffled across time.
DATA_START = "2014-01-01"
TRAIN_END = "2021-12-31"
VAL_END = "2022-12-31"  # validation = 2022 (early stopping) ; test = 2023-01-01 -> latest

# Model inputs (keep in sync with the service).
FEATURES = ["et0", "rain", "tmax", "tmin", "doy_sin", "doy_cos"]
WINDOW = 30  # days of history given to the model
HORIZON = 16  # days predicted at once (Open-Meteo forecasts go up to 16 days)
EVAL_HORIZON = 7  # the farmer's plan is 7 days: metrics on horizons 1..7

log = logging.getLogger("m2")


# --------------------------------------------------------------------------- data


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
    except ImportError:  # pragma: no cover
        pass


def _get_json(url: str, params: dict, retries: int = 6) -> dict:
    query = urllib.parse.urlencode(params, safe=",")
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(f"{url}?{query}", timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:  # network hiccups, "service overloaded"...
            last_error = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Open-Meteo unreachable after {retries} attempts: {last_error}")


def fetch_region(name: str, end: str, force: bool = False) -> pd.DataFrame:
    """ERA5 daily weather of one governorate, cached in data/raw/m2_irrigation/<name>.csv (never edited)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{name}.csv"
    if path.exists() and not force:
        return pd.read_csv(path, parse_dates=["date"])
    lat, lon = REGIONS[name]
    payload = _get_json(
        ARCHIVE_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "start_date": DATA_START,
            "end_date": end,
            "daily": ",".join(DAILY_VARS),
            "timezone": "Africa/Tunis",
        },
    )
    daily = payload["daily"]
    df = pd.DataFrame({"date": pd.to_datetime(daily["time"])})
    for api_name, short in COLUMNS.items():
        df[short] = daily[api_name]
    df.to_csv(path, index=False)
    return df


def load_all(end: str | None = None, force: bool = False) -> pd.DataFrame:
    """All regions stacked: columns region, date, et0, rain, tmax, tmin (+ day-of-year features)."""
    end = end or (pd.Timestamp.today().normalize() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")  # ERA5 lag ~5 d
    frames = []
    for name in REGIONS:
        df = fetch_region(name, end, force=force)
        df.insert(0, "region", name)
        frames.append(df)
    data = pd.concat(frames, ignore_index=True)
    return add_calendar(data)


def add_calendar(df: pd.DataFrame) -> pd.DataFrame:
    doy = df["date"].dt.dayofyear
    df["doy_sin"] = np.sin(2 * math.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * math.pi * doy / 365.25)
    return df


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Drop trailing empty days (ERA5 not yet available), interpolate rare holes. Returns (data, report)."""
    report = df.groupby("region")[["et0", "rain", "tmax", "tmin"]].apply(lambda g: g.isna().sum())
    out = []
    for _, g in df.groupby("region", sort=False):
        g = g.sort_values("date")
        last_valid = g["et0"].last_valid_index()
        g = g.loc[:last_valid].copy()
        g[["et0", "tmax", "tmin"]] = g[["et0", "tmax", "tmin"]].interpolate(limit=3)
        g["rain"] = g["rain"].fillna(0.0)
        out.append(g.dropna(subset=["et0", "tmax", "tmin"]))
    return pd.concat(out, ignore_index=True), report


# --------------------------------------------------------------------------- windows


@dataclass
class Norm:
    mean: np.ndarray
    std: np.ndarray

    @classmethod
    def fit(cls, train: pd.DataFrame) -> Norm:
        values = train[FEATURES].to_numpy(dtype=np.float64)
        std = values.std(axis=0)
        std[std == 0] = 1.0
        return cls(values.mean(axis=0), std)

    def apply(self, values: np.ndarray) -> np.ndarray:
        return (values - self.mean) / self.std


def windows(df: pd.DataFrame, norm: Norm, origin_start: str, origin_end: str) -> tuple[np.ndarray, np.ndarray, list]:
    """Samples whose origin day t (last input day) is in [origin_start, origin_end].

    X = features of days t-WINDOW+1..t (normalised), y = ET0 of days t+1..t+HORIZON (mm, raw).
    Returns X, y and the (region, origin date) index of each sample.
    """
    xs, ys, index = [], [], []
    lo, hi = pd.Timestamp(origin_start), pd.Timestamp(origin_end)
    for region, g in df.groupby("region", sort=False):
        g = g.sort_values("date").reset_index(drop=True)
        feats = norm.apply(g[FEATURES].to_numpy(dtype=np.float64))
        et0 = g["et0"].to_numpy(dtype=np.float64)
        dates = g["date"].to_numpy()
        for t in range(WINDOW - 1, len(g) - HORIZON):
            d = pd.Timestamp(dates[t])
            if d < lo or d > hi:
                continue
            xs.append(feats[t - WINDOW + 1 : t + 1])
            ys.append(et0[t + 1 : t + 1 + HORIZON])
            index.append((region, d))
    return np.asarray(xs, dtype=np.float32), np.asarray(ys, dtype=np.float32), index


# --------------------------------------------------------------------------- baselines


def baseline_last_year(df: pd.DataFrame, index: list) -> np.ndarray:
    """ET0 forecast = ET0 observed the same calendar day one year earlier (the roadmap baseline)."""
    lookup = df.set_index(["region", "date"])["et0"]
    preds = np.zeros((len(index), HORIZON), dtype=np.float32)
    for i, (region, origin) in enumerate(index):
        for h in range(HORIZON):
            day = origin + pd.Timedelta(days=h + 1) - pd.DateOffset(years=1)
            preds[i, h] = lookup.get((region, day), np.nan)
    return preds


def baseline_persistence(df: pd.DataFrame, index: list) -> np.ndarray:
    """ET0 forecast = mean ET0 of the last 7 observed days (second, stronger naive reference)."""
    preds = np.zeros((len(index), HORIZON), dtype=np.float32)
    by_region = {r: g.set_index("date")["et0"] for r, g in df.groupby("region")}
    for i, (region, origin) in enumerate(index):
        s = by_region[region]
        preds[i, :] = s.loc[origin - pd.Timedelta(days=6) : origin].mean()
    return preds


# --------------------------------------------------------------------------- Prophet


def prophet_forecasts(df: pd.DataFrame, index: list, history_years: int = 6) -> np.ndarray:
    """One univariate Prophet model per (region, origin), fitted on the data before the origin."""
    from prophet import Prophet

    for name in ("cmdstanpy", "prophet"):  # one INFO line per fit otherwise (hundreds of fits)
        logging.getLogger(name).setLevel(logging.ERROR)
        logging.getLogger(name).propagate = False
    logging.getLogger("cmdstanpy").disabled = True
    by_region = {r: g.set_index("date")["et0"] for r, g in df.groupby("region")}
    preds = np.zeros((len(index), HORIZON), dtype=np.float32)
    for i, (region, origin) in enumerate(index):
        s = by_region[region]
        hist = s.loc[origin - pd.DateOffset(years=history_years) : origin]
        model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        model.fit(pd.DataFrame({"ds": hist.index, "y": hist.to_numpy()}))
        future = pd.DataFrame({"ds": pd.date_range(origin + pd.Timedelta(days=1), periods=HORIZON, freq="D")})
        preds[i, :] = np.clip(model.predict(future)["yhat"].to_numpy(), 0, None)
    return preds


# --------------------------------------------------------------------------- LSTM


def build_lstm(hidden: int = 64):
    import torch
    from torch import nn

    class Et0Lstm(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(input_size=len(FEATURES), hidden_size=hidden, num_layers=1, batch_first=True)
            self.head = nn.Linear(hidden, HORIZON)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            _, (h, _) = self.lstm(x)
            return self.head(h[-1])

    return Et0Lstm()


def train_lstm(x_train, y_train, x_val, y_val, et0_mean: float, et0_std: float, epochs: int = 60, patience: int = 8):
    """Adam + MSE on standardised ET0, early stopping on validation MAE. Returns (model, history)."""
    import torch

    set_seed()
    model = build_lstm()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = torch.nn.MSELoss()
    xt, yt = torch.from_numpy(x_train), torch.from_numpy((y_train - et0_mean) / et0_std)
    xv = torch.from_numpy(x_val)
    best_mae, best_state, bad, history = float("inf"), None, 0, []
    generator = torch.Generator().manual_seed(SEED)
    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(len(xt), generator=generator)
        total = 0.0
        for start in range(0, len(xt), 256):
            idx = perm[start : start + 256]
            optimizer.zero_grad()
            loss = loss_fn(model(xt[idx]), yt[idx])
            loss.backward()
            optimizer.step()
            total += loss.item() * len(idx)
        model.eval()
        with torch.no_grad():
            val_pred = model(xv).numpy() * et0_std + et0_mean
        val_mae = float(np.mean(np.abs(val_pred[:, :EVAL_HORIZON] - y_val[:, :EVAL_HORIZON])))
        history.append({"epoch": epoch + 1, "train_mse": total / len(xt), "val_mae": val_mae})
        if val_mae < best_mae - 1e-4:
            best_mae, bad = val_mae, 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    model.load_state_dict(best_state)
    model.eval()
    return model, pd.DataFrame(history)


def lstm_predict(model, x: np.ndarray, et0_mean: float, et0_std: float) -> np.ndarray:
    import torch

    with torch.no_grad():
        out = model(torch.from_numpy(x)).numpy() * et0_std + et0_mean
    return np.clip(out, 0, None)


def numpy_lstm_forward(weights: dict, x: np.ndarray) -> np.ndarray:
    """Same forward pass as the service (NumPy only). x: (batch, WINDOW, features) normalised."""

    def sigmoid(v):
        return 1.0 / (1.0 + np.exp(-v))

    w_ih, w_hh = weights["w_ih"], weights["w_hh"]
    bias = weights["b_ih"] + weights["b_hh"]
    hidden = w_hh.shape[1]
    h = np.zeros((x.shape[0], hidden))
    c = np.zeros((x.shape[0], hidden))
    for t in range(x.shape[1]):
        gates = x[:, t, :] @ w_ih.T + h @ w_hh.T + bias
        i, f, g, o = np.split(gates, 4, axis=1)  # PyTorch gate order
        c = sigmoid(f) * c + sigmoid(i) * np.tanh(g)
        h = sigmoid(o) * np.tanh(c)
    out = h @ weights["head_w"].T + weights["head_b"]
    return np.clip(out * weights["et0_std"] + weights["et0_mean"], 0, None)


def lstm_weights(model, norm: Norm, et0_mean: float, et0_std: float) -> dict:
    state = {k: v.detach().cpu().numpy().astype(np.float64) for k, v in model.state_dict().items()}
    return {
        "w_ih": state["lstm.weight_ih_l0"],
        "w_hh": state["lstm.weight_hh_l0"],
        "b_ih": state["lstm.bias_ih_l0"],
        "b_hh": state["lstm.bias_hh_l0"],
        "head_w": state["head.weight"],
        "head_b": state["head.bias"],
        "feat_mean": norm.mean,
        "feat_std": norm.std,
        "et0_mean": np.float64(et0_mean),
        "et0_std": np.float64(et0_std),
        "window": np.int64(WINDOW),
        "horizon": np.int64(HORIZON),
    }


# --------------------------------------------------------------------------- metrics


def metrics(y_true: np.ndarray, y_pred: np.ndarray, horizon: int = EVAL_HORIZON) -> dict:
    t, p = y_true[:, :horizon], y_pred[:, :horizon]
    mask = ~np.isnan(p)
    err = p[mask] - t[mask]
    return {"MAE": float(np.mean(np.abs(err))), "RMSE": float(np.sqrt(np.mean(err**2)))}


def metrics_by_horizon(y_true: np.ndarray, y_pred: np.ndarray, horizon: int = EVAL_HORIZON) -> list[float]:
    return [float(np.nanmean(np.abs(y_pred[:, h] - y_true[:, h]))) for h in range(horizon)]


def export(weights: dict, metadata: dict) -> dict:
    """models/m2/lstm_et0.npz (weights + normalisation) and metadata.json (metrics, data, versions)."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(MODEL_DIR / "lstm_et0.npz", **weights)
    meta = {**metadata, "features": FEATURES, "window": WINDOW, "horizon": HORIZON, "seed": SEED}
    (MODEL_DIR / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return {name: str(MODEL_DIR / name) for name in ["lstm_et0.npz", "metadata.json"]}
