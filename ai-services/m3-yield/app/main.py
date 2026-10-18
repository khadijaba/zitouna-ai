"""M3 · Yield forecast. Thin FastAPI wrapper: no business logic, no database."""

from fastapi import FastAPI, HTTPException

from app import predictor
from app.schemas import YieldRequest, YieldResponse

app = FastAPI(title="Zitouna M3 · Yield forecast", version="1.0", docs_url=None, redoc_url=None, openapi_url=None)
model = predictor.load()  # None -> mock mode


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "module": "m3-yield", "modelLoaded": model is not None}


@app.post("/predict", response_model=YieldResponse)
def predict(request: YieldRequest) -> YieldResponse:
    try:
        return predictor.predict(model, request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
