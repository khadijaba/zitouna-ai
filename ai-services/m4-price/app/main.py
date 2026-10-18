"""M4 · Price forecast and selling advice. Thin FastAPI wrapper: no business logic, no database."""

from fastapi import FastAPI

from app import predictor
from app.schemas import PriceRequest, PriceResponse

app = FastAPI(title="Zitouna M4 · Price & selling time", version="1.0", docs_url=None, redoc_url=None, openapi_url=None)
model = predictor.load()  # None -> mock mode


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "module": "m4-price", "modelLoaded": model is not None}


@app.post("/predict", response_model=PriceResponse)
def predict(request: PriceRequest) -> PriceResponse:
    return predictor.predict(model, request)
