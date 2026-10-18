import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """snake_case in Python, camelCase in JSON (the contract with the Spring backend)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class IrrigationRequest(CamelModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    tree_count: int | None = Field(default=None, ge=0)
    area_ha: float | None = Field(default=None, gt=0)
    days: int = Field(default=7, ge=1, le=16)


class Day(CamelModel):
    date: dt.date
    et0_mm: float
    rain_mm: float
    water_need_mm: float  # ET0 x Kc - effective rain
    liters_per_tree: float | None = None
    irrigate: bool


class Alert(CamelModel):
    date: dt.date
    type: Literal["FROST", "HEATWAVE"]
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    message: str


class IrrigationResponse(CamelModel):
    days: list[Day]
    alerts: list[Alert]
    model_version: str
    mock: bool
