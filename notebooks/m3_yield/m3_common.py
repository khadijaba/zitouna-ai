"""M3 · Yield forecast — shared code for the notebook (train_m3.ipynb).

Plan B of the roadmap (yield data per governorate not available): forecast the **national** olive production
of Tunisia for a season, from FAOSTAT (production, harvested area, 1961 -> last year) and seasonal ERA5
weather averaged over the 12 main olive governorates (Open-Meteo), then derive the yield per hectare / per
tree for the parcel.

Season Y = harvest that starts in autumn Y (FAO convention: a crop harvested over two calendar years is
recorded in the year the harvest begins), the same convention as the API (2026 = 2026/2027).
"""

from __future__ import annotations

import io
import json
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "m3_yield"
MODEL_DIR = ROOT / "models" / "m3"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

SEED = 42
FAOSTAT_URL = "https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Africa.zip"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
WEATHER_START = "1960-01-01"

# Same governorates as M2 (capital coordinates).
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

# Features used by every model (keep in sync with ai-services/m3-yield/app/predictor.py).
FEATURES = [
    "lag1_log",  # log production of the previous season (alternate bearing: good year / bad year)
    "lag2_log",  # two seasons before
    "trend",  # season - 1961 (plantations keep growing)
    "rain_sep_may",  # rain from September Y-1 to May Y (mm), water available for flowering and fruit set
    "rain_jun_aug",  # summer rain of season Y (mm)
    "heat_days_apr_may",  # days with Tmax >= 35 °C in April-May Y (heat at flowering)
    "tmax_jun_aug",  # mean Tmax June-August Y (°C)
]
TARGET = "log_production"


def _download(url: str, retries: int = 6, timeout: int = 600) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "zitouna-ai-notebook"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as e:
            last_error = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"download failed after {retries} attempts: {url}: {last_error}")


def load_faostat(force: bool = False) -> pd.DataFrame:
    """Tunisia, item Olives (260): production (t), area harvested (ha), yield (kg/ha) per year."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = RAW_DIR / "faostat_africa.zip"
    if force or not zip_path.exists():
        zip_path.write_bytes(_download(FAOSTAT_URL))
    with zipfile.ZipFile(zip_path) as z:
        with z.open("Production_Crops_Livestock_E_Africa_NOFLAG.csv") as f:
            raw = pd.read_csv(io.TextIOWrapper(f, encoding="latin-1"))
    rows = raw[(raw["Area"] == "Tunisia") & (raw["Item"] == "Olives")]
    years = [c for c in raw.columns if c.startswith("Y") and c[1:].isdigit()]
    long = rows.melt(id_vars=["Element"], value_vars=years, var_name="year", value_name="value")
    long["year"] = long["year"].str[1:].astype(int)
    wide = long.pivot_table(index="year", columns="Element", values="value").rename(
        columns={"Production": "production_t", "Area harvested": "area_ha", "Yield": "yield_kg_ha"}
    )
    return wide[["production_t", "area_ha", "yield_kg_ha"]].dropna(subset=["production_t"]).sort_index()


def _get_json(url: str, params: dict) -> dict:
    return json.loads(_download(f"{url}?{urllib.parse.urlencode(params, safe=',')}"))


def load_weather(end: str | None = None, force: bool = False) -> pd.DataFrame:
    """Daily ERA5 (rain, Tmax) of the 12 governorates since 1960, cached in data/raw/m3_yield/weather_<region>.csv."""
    end = end or (pd.Timestamp.today().normalize() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    frames = []
    for name, (lat, lon) in REGIONS.items():
        path = RAW_DIR / f"weather_{name}.csv"
        if force or not path.exists():
            payload = _get_json(
                ARCHIVE_URL,
                {
                    "latitude": lat,
                    "longitude": lon,
                    "start_date": WEATHER_START,
                    "end_date": end,
                    "daily": "precipitation_sum,temperature_2m_max",
                    "timezone": "Africa/Tunis",
                },
            )
            daily = payload["daily"]
            pd.DataFrame(
                {"date": daily["time"], "rain": daily["precipitation_sum"], "tmax": daily["temperature_2m_max"]}
            ).to_csv(path, index=False)
        df = pd.read_csv(path, parse_dates=["date"])
        df["region"] = name
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def seasonal_weather(daily: pd.DataFrame) -> pd.DataFrame:
    """One row per season Y: weather features averaged over the 12 governorates."""
    d = daily.dropna(subset=["rain", "tmax"]).copy()
    d["year"], d["month"] = d["date"].dt.year, d["date"].dt.month
    # Sep-Dec of year Y-1 belong to the rain season of Y.
    d["rain_season"] = np.where(d["month"] >= 9, d["year"] + 1, d["year"])
    per_region = []
    for _, g in d.groupby("region"):
        rain_sep_may = g[g["month"].isin([9, 10, 11, 12, 1, 2, 3, 4, 5])].groupby("rain_season")["rain"].sum()
        summer = g[g["month"].isin([6, 7, 8])].groupby("year")
        spring = g[g["month"].isin([4, 5])].groupby("year")
        per_region.append(
            pd.DataFrame(
                {
                    "rain_sep_may": rain_sep_may,
                    "rain_jun_aug": summer["rain"].sum(),
                    "heat_days_apr_may": spring["tmax"].apply(lambda t: (t >= 35).sum()),
                    "tmax_jun_aug": summer["tmax"].mean(),
                    "days_sep_may": g[g["month"].isin([9, 10, 11, 12, 1, 2, 3, 4, 5])].groupby("rain_season").size(),
                    "days_jun_aug": summer.size(),
                }
            )
        )
    out = pd.concat(per_region).groupby(level=0).mean()
    # Keep complete seasons only (273 days Sep-May, 92 days Jun-Aug, minus a few missing days).
    out = out[(out["days_sep_may"] >= 270) & (out["days_jun_aug"] >= 90)]
    out.index.name = "season"
    return out.drop(columns=["days_sep_may", "days_jun_aug"])


def build_dataset(fao: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    df = fao.join(weather, how="inner")
    df[TARGET] = np.log(df["production_t"])
    df["lag1_log"] = np.log(fao["production_t"]).shift(1).reindex(df.index)
    df["lag2_log"] = np.log(fao["production_t"]).shift(2).reindex(df.index)
    df["trend"] = df.index - 1961
    return df.dropna(subset=FEATURES + [TARGET])


def features_for_season(season: int, fao: pd.DataFrame, weather: pd.DataFrame) -> dict | None:
    """Feature row for a season to forecast (its production unknown); None if inputs are missing."""
    prev = np.log(fao["production_t"])
    if season - 1 not in prev.index or season - 2 not in prev.index or season not in weather.index:
        return None
    row = {"lag1_log": prev[season - 1], "lag2_log": prev[season - 2], "trend": season - 1961}
    row.update(weather.loc[season, ["rain_sep_may", "rain_jun_aug", "heat_days_apr_may", "tmax_jun_aug"]].to_dict())
    return row


def models() -> dict:
    """Linear regression (roadmap baseline) vs tree ensembles; the tree models see the same features."""
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import LinearRegression, RidgeCV
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return {
        "Régression linéaire (baseline)": make_pipeline(StandardScaler(), LinearRegression()),
        "Ridge": make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 30))),
        "Random Forest": RandomForestRegressor(n_estimators=500, min_samples_leaf=2, random_state=SEED),
        "Gradient Boosting": GradientBoostingRegressor(
            n_estimators=300, learning_rate=0.03, max_depth=2, subsample=0.8, random_state=SEED
        ),
    }


def rolling_forecasts(df: pd.DataFrame, model_factory, first_test_season: int) -> pd.Series:
    """Expanding window: each test season is predicted by a model trained only on the previous seasons."""
    preds = {}
    for season in df.index[df.index >= first_test_season]:
        train = df[df.index < season]
        model = model_factory()
        model.fit(train[FEATURES], train[TARGET])
        preds[season] = float(np.exp(model.predict(df.loc[[season], FEATURES])[0]))
    return pd.Series(preds, name="pred_t")


def metrics(actual: pd.Series, pred: pd.Series) -> dict:
    err = pred - actual
    return {
        "MAE (t)": float(err.abs().mean()),
        "MAPE (%)": float((err.abs() / actual).mean() * 100),
        "RMSE (t)": float(np.sqrt((err**2).mean())),
    }


def export(files: dict[str, object], metadata: dict) -> dict:
    """models/m3/: model.joblib (fitted pipeline), history.csv (FAOSTAT + seasonal weather), metadata.json."""
    import joblib

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, content in files.items():
        path = MODEL_DIR / name
        if name.endswith(".joblib"):
            joblib.dump(content, path)
        elif isinstance(content, pd.DataFrame):
            content.to_csv(path)
        else:
            path.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
        written[name] = str(path)
    (MODEL_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    written["metadata.json"] = str(MODEL_DIR / "metadata.json")
    return written
