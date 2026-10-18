"""M4 · Price & selling time — shared code for the notebook (train_m4.ipynb).

Pipeline: monthly olive-oil price (IMF series via FRED, or COI Tunisian producer prices when the team has
typed them in) converted to TND/kg -> chronological split -> naive baseline -> SARIMA -> LSTM ->
evaluation (MAPE per horizon + simulated gain of the sell/store advice against "always sell now")
-> export for the FastAPI service.

The service (ai-services/m4-price/app/predictor.py) re-fits the exported SARIMA order on the exported
series at start-up: keep TRANSFORM / STORAGE_COST identical in both files.
"""

from __future__ import annotations

import json
import math
import random
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "m4_price"
MODEL_DIR = ROOT / "models" / "m4"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

SEED = 42
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=POLVOILUSDM"
WORLD_BANK_FX_URL = "https://api.worldbank.org/v2/country/TUN/indicator/PA.NUS.FCRF?format=json&per_page=100"
COI_FILE = RAW_DIR / "coi_tunisia_producer.csv"  # optional: date (YYYY-MM), price_tnd_kg — typed from COI bulletins

TRAIN_END = "2016-12-01"
VAL_END = "2020-12-01"  # validation 2017–2020 (SARIMA order, LSTM early stopping); test 2021-01 -> latest
HORIZON = 6  # months; the app asks up to 26 weeks
WINDOW = 24  # months of history given to the LSTM
STORAGE_COST = 0.15  # TND per kg of oil per month (same constant as the service)


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
    except ImportError:  # pragma: no cover
        pass


# --------------------------------------------------------------------------- data


def _download(url: str, retries: int = 6) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "zitouna-ai-notebook"})
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except Exception as e:
            last_error = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"download failed after {retries} attempts: {url}: {last_error}")


def fetch_imf_price(force: bool = False) -> pd.DataFrame:
    """IMF 'Global price of Olive Oil' (extra virgin, UK ex-tanker), USD per tonne, monthly (FRED POLVOILUSDM)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / "POLVOILUSDM.csv"
    if force or not path.exists():
        path.write_bytes(_download(FRED_URL))
    df = pd.read_csv(path)
    df.columns = ["date", "usd_t"]
    df["date"] = pd.to_datetime(df["date"])
    df["usd_t"] = pd.to_numeric(df["usd_t"], errors="coerce")
    return df.dropna()


def fetch_fx(force: bool = False) -> pd.DataFrame:
    """World Bank official exchange rate, TND per USD, yearly average (PA.NUS.FCRF)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / "fx_tnd_per_usd.csv"
    if force or not path.exists():
        payload = json.loads(_download(WORLD_BANK_FX_URL))
        rows = [(int(r["date"]), r["value"]) for r in payload[1] if r["value"] is not None]
        pd.DataFrame(rows, columns=["year", "tnd_per_usd"]).sort_values("year").to_csv(path, index=False)
    return pd.read_csv(path)


def build_series(force: bool = False) -> tuple[pd.DataFrame, str]:
    """Monthly series indexed by month start: price (TND per kg of oil) + the raw columns. Returns (df, source)."""
    if COI_FILE.exists():
        coi = pd.read_csv(COI_FILE)
        if len(coi) >= 60:
            coi["date"] = pd.to_datetime(coi["date"]).dt.to_period("M").dt.to_timestamp()
            df = coi.set_index("date").sort_index()[["price_tnd_kg"]].rename(columns={"price_tnd_kg": "price"})
            return df, "COI — prix au producteur Tunisie (saisis depuis les bulletins mensuels)"
    imf = fetch_imf_price(force)
    fx = fetch_fx(force).set_index("year")["tnd_per_usd"]
    imf["year"] = imf["date"].dt.year
    # Years not yet published by the World Bank use the last known yearly rate.
    imf["tnd_per_usd"] = imf["year"].map(lambda y: fx.get(y, fx.loc[fx.index.max()] if y > fx.index.max() else np.nan))
    imf = imf.dropna(subset=["tnd_per_usd"])
    imf["price"] = imf["usd_t"] / 1000 * imf["tnd_per_usd"]
    df = imf.set_index("date")[["price", "usd_t", "tnd_per_usd"]]
    df.index.freq = "MS"
    return df, "FMI — prix mondial de l'huile d'olive extra vierge (FRED POLVOILUSDM), converti en TND (Banque mondiale)"


# --------------------------------------------------------------------------- forecasting


def naive_forecast(log_hist: np.ndarray) -> np.ndarray:
    return np.repeat(log_hist[-1], HORIZON)


def select_sarima(log_series: pd.Series) -> tuple[tuple, tuple, pd.DataFrame]:
    """Small grid on (p,1,q)(P,0,Q,12), chosen by AIC on train + validation."""
    import warnings

    from statsmodels.tsa.statespace.sarimax import SARIMAX

    rows = []
    for p in range(3):
        for q in range(3):
            for big_p in range(2):
                for big_q in range(2):
                    order, seasonal = (p, 1, q), (big_p, 0, big_q, 12)
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        try:
                            res = SARIMAX(log_series, order=order, seasonal_order=seasonal).fit(disp=False)
                            rows.append({"order": order, "seasonal_order": seasonal, "aic": res.aic})
                        except Exception:
                            continue
    table = pd.DataFrame(rows).sort_values("aic").reset_index(drop=True)
    best = table.iloc[0]
    return tuple(best["order"]), tuple(best["seasonal_order"]), table


def sarima_forecast(log_hist: pd.Series, order: tuple, seasonal: tuple, alpha: float = 0.2):
    """Mean and (1-alpha) interval of the log price, HORIZON months ahead."""
    import warnings

    from statsmodels.tsa.statespace.sarimax import SARIMAX

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = SARIMAX(log_hist, order=order, seasonal_order=seasonal).fit(disp=False)
        fc = res.get_forecast(HORIZON)
        ci = np.asarray(fc.conf_int(alpha=alpha))
    return np.asarray(fc.predicted_mean), ci[:, 0], ci[:, 1]


# --------------------------------------------------------------------------- LSTM


def lstm_features(log_price: pd.Series) -> np.ndarray:
    """Per month: log-return, sin / cos of the month."""
    ret = log_price.diff().fillna(0.0).to_numpy()
    month = log_price.index.month.to_numpy()
    return np.column_stack([ret, np.sin(2 * math.pi * month / 12), np.cos(2 * math.pi * month / 12)])


def lstm_samples(log_price: pd.Series, origin_start: str, origin_end: str):
    """X: WINDOW months of features ending at origin t ; y: log(P[t+h]) - log(P[t]), h = 1..HORIZON."""
    feats = lstm_features(log_price)
    values = log_price.to_numpy()
    dates = log_price.index
    xs, ys, origins = [], [], []
    for t in range(WINDOW, len(values) - HORIZON):
        if pd.Timestamp(origin_start) <= dates[t] <= pd.Timestamp(origin_end):
            xs.append(feats[t - WINDOW + 1 : t + 1])
            ys.append(values[t + 1 : t + 1 + HORIZON] - values[t])
            origins.append(dates[t])
    return np.asarray(xs, dtype=np.float32), np.asarray(ys, dtype=np.float32), origins


def lstm_inputs(log_price: pd.Series, origins: list) -> np.ndarray:
    """X for any origin, even when its future is not observed yet (end of the test set, production)."""
    feats = lstm_features(log_price)
    position = {d: i for i, d in enumerate(log_price.index)}
    return np.asarray([feats[position[d] - WINDOW + 1 : position[d] + 1] for d in origins], dtype=np.float32)


def train_lstm_ensemble(x_train, y_train, x_val, y_val, seeds=(42, 43, 44, 45, 46), epochs=300, patience=30):
    """Small LSTM (32 units), Adam + MSE, early stopping on validation; averaged over 5 seeds (few data)."""
    import torch
    from torch import nn

    class PriceLstm(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(input_size=3, hidden_size=32, batch_first=True)
            self.head = nn.Linear(32, HORIZON)

        def forward(self, x):
            _, (h, _) = self.lstm(x)
            return self.head(h[-1])

    scale = float(y_train.std()) or 1.0
    xt, yt, xv = torch.from_numpy(x_train), torch.from_numpy(y_train / scale), torch.from_numpy(x_val)
    models = []
    for seed in seeds:
        set_seed(seed)
        model = PriceLstm()
        optimizer = torch.optim.Adam(model.parameters(), lr=3e-3, weight_decay=1e-4)
        best, best_state, bad = float("inf"), None, 0
        for _ in range(epochs):
            model.train()
            optimizer.zero_grad()
            loss = nn.functional.mse_loss(model(xt), yt)
            loss.backward()
            optimizer.step()
            model.eval()
            with torch.no_grad():
                val = float(np.mean(np.abs(model(xv).numpy() * scale - y_val)))
            if val < best - 1e-5:
                best, bad, best_state = val, 0, {k: v.clone() for k, v in model.state_dict().items()}
            else:
                bad += 1
                if bad >= patience:
                    break
        model.load_state_dict(best_state)
        model.eval()
        models.append(model)
    return models, scale


def lstm_ensemble_predict(models, scale: float, x: np.ndarray) -> np.ndarray:
    import torch

    with torch.no_grad():
        return np.mean([m(torch.from_numpy(x)).numpy() * scale for m in models], axis=0)


# --------------------------------------------------------------------------- evaluation


def mape_by_horizon(actual: np.ndarray, pred: np.ndarray) -> np.ndarray:
    """actual / pred: (origins, HORIZON) prices, NaN where the future is not observed yet."""
    return np.nanmean(np.abs(pred - actual) / actual, axis=0) * 100


def sell_or_store(current: float, forecast: np.ndarray, min_gain: float = 0.0) -> int:
    """Months to wait (0 = sell now).

    Store only if the best forecast price, minus the storage cost, beats today's price by more than
    `min_gain` (a share of today's price: 0.05 = 5 %). The margin protects against forecast errors.
    """
    gains = [forecast[h] - STORAGE_COST * (h + 1) - current for h in range(len(forecast))]
    best = int(np.argmax(gains))
    return best + 1 if gains[best] > min_gain * current else 0


def simulate_strategy(prices: np.ndarray, forecasts: np.ndarray, min_gain: float = 0.0) -> pd.DataFrame:
    """For every origin with 6 observed future months: TND/kg obtained by the advice vs selling right away."""
    rows = []
    for k in range(len(prices)):
        current, future, fc = prices[k, 0], prices[k, 1:], forecasts[k]
        if np.isnan(future).any():
            continue
        wait = sell_or_store(current, fc, min_gain)
        obtained = current if wait == 0 else future[wait - 1] - STORAGE_COST * wait
        best_possible = max([current] + [future[h] - STORAGE_COST * (h + 1) for h in range(HORIZON)])
        rows.append({"wait_months": wait, "obtained": obtained, "sell_now": current, "oracle": best_possible})
    df = pd.DataFrame(rows)
    df["gain"] = df["obtained"] - df["sell_now"]
    return df


def strategy_summary(sim: pd.DataFrame) -> dict:
    stored = sim["wait_months"] > 0
    return {
        "décisions": len(sim),
        "% stocker": 100 * stored.mean(),
        "gain moyen (TND/kg)": sim["gain"].mean(),
        "% stockages gagnants": 100 * (sim.loc[stored, "gain"] > 0).mean() if stored.any() else np.nan,
        "pire perte (TND/kg)": sim["gain"].min(),
        "gain oracle (TND/kg)": (sim["oracle"] - sim["sell_now"]).mean(),
    }


def export(files: dict[str, object], metadata: dict) -> dict:
    """Writes models/m4/: model.json, prices.csv, metadata.json (+ lstm weights if any)."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, content in files.items():
        path = MODEL_DIR / name
        if isinstance(content, pd.DataFrame):
            content.to_csv(path, index=True)
        elif isinstance(content, dict) and name.endswith(".npz"):
            np.savez(path, **content)
        else:
            path.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
        written[name] = str(path)
    (MODEL_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    written["metadata.json"] = str(MODEL_DIR / "metadata.json")
    return written


