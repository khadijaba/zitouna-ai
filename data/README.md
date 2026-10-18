# Data

Datasets are **not in Git**. They live in the team's shared Google Drive folder `zitouna-ai/data/`, with the same structure as here. Download what you need into `data/raw/` and `data/processed/` on your machine.

## Rules (same for every module)

1. `data/raw/` — downloads and source PDFs, **never modified**. Keep each ONAGRI/COI PDF next to the CSV extracted from it.
2. `data/processed/` — cleaned data ready for training, produced by a notebook or script in `notebooks/mX_*/`.
3. Images: 70 / 15 / 15 stratified split. Time series: chronological split, never shuffled.
4. Harmonize units (tonnes, TND/kg, €/kg) and governorate names (use the list in `frontend/src/app/features/parcels/parcel-list.ts`).
5. Write a short EDA summary per module (reused in the final report).

## Catalog

| Dataset | Module | Where to get it | Folder | Effort |
|---|---|---|---|---|
| Olive leaf disease (Uğuz & Uysal), 3 400 images, 3 classes | M1 | Kaggle mirrors, search "olive leaf disease" | `raw/m1/uguz/` | Low |
| Roboflow "olive's leaf diseases" (CC BY 4.0), adds olive knot | M1 | Roboflow export (free account) | `raw/m1/roboflow/` | Low |
| Open-Meteo ERA5 history + forecasts | M2, M3 | `archive-api.open-meteo.com` or `openmeteo-requests` | `raw/m2/openmeteo/` | Low |
| FAOSTAT production & producer prices, Tunisia | M3, M4 | CSV export from fao.org/faostat | `raw/m3/faostat/` | Low |
| ONAGRI reports (production per governorate, exports, prices) | M3, M4 | PDF → `pdfplumber` / `camelot` or manual entry | `raw/m3/onagri/` | **High** |
| International Olive Council monthly producer prices | M4 | Monthly bulletins → CSV | `raw/m4/coi/` | Medium |
| TUNIZI (9 000+ Tunisian arabizi sentences) | M5 | GitHub / Hugging Face `tunizi` | `raw/m5/tunizi/` | Low |
| Farmer questions per intent (300–500) | M5 | Written by the team | `raw/m5/questions.csv` | Medium |
| Agricultural guides (FAO, COI, ministry), 20–40 PDFs | M5 | Manual collection | `raw/m5/guides/` | Low |
| OliveTreeCrownsDb (drone tiles, annotated crowns) | M6 | Mendeley Data | `raw/m6/olivetreecrowns/` | Low |

ONAGRI and COI extraction is the main project risk: M3 and M4 start it in week 1 and split the work.
