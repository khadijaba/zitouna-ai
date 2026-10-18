import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """snake_case in Python, camelCase in JSON (the contract with the Spring backend)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PriceRequest(CamelModel):
    horizon_weeks: int = Field(default=8, ge=1, le=26)
    quantity_kg: float | None = Field(default=None, ge=0, description="kg of oil the farmer could sell")


class Point(CamelModel):
    date: dt.date
    price: float
    low: float | None = None
    high: float | None = None


class PriceResponse(CamelModel):
    currency: str = "TND"
    unit: str = "kg"
    history: list[Point]
    forecast: list[Point]
    recommendation: Literal["SELL_NOW", "STORE"]
    reason: str
    expected_gain_tnd: float | None = None
    model_version: str
    mock: bool
    # Additive (the Spring DTO ignores unknown fields): where the prices come from, null in mock mode.
    source: str | None = None
