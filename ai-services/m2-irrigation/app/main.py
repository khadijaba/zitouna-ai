"""M2 · Irrigation and weather alerts. Thin FastAPI wrapper: no business logic, no database."""

from fastapi import FastAPI

from app import predictor
from app.schemas import IrrigationRequest, IrrigationResponse

app = FastAPI(
    title="Zitouna M2 · Irrigation & weather alerts", version="1.0", docs_url=None, redoc_url=None, openapi_url=None
)
model = predictor.load()  # None -> mock mode


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "module": "m2-irrigation", "modelLoaded": model is not None}


@app.post("/predict", response_model=IrrigationResponse)
def predict(request: IrrigationRequest) -> IrrigationResponse:
    return predictor.predict(model, request)
