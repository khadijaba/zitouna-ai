"""M6 · Olive tree counting. Thin FastAPI wrapper: no business logic, no database."""

from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile

from app import predictor
from app.schemas import TreeCountResponse

app = FastAPI(title="Zitouna M6 · Olive tree counting", version="1.0", docs_url=None, redoc_url=None, openapi_url=None)
model = predictor.load()  # None -> mock mode


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "module": "m6-tree-count", "modelLoaded": model is not None}


@app.post("/predict", response_model=TreeCountResponse)
async def predict(image: Annotated[UploadFile, File()]) -> TreeCountResponse:
    data = await image.read()
    try:
        return predictor.predict(model, data)
    except predictor.InvalidImageError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
