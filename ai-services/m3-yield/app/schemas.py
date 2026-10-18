from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """snake_case in Python, camelCase in JSON (the contract with the Spring backend)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class YieldRequest(CamelModel):
    governorate: str = Field(min_length=2, examples=["Sfax"])
    season: int = Field(ge=1961, le=2100, description="Year the harvest starts: 2026 = season 2026/2027")
    tree_count: int | None = Field(default=None, ge=0)
    area_ha: float | None = Field(default=None, gt=0, description="Parcel area: better estimate than the tree count")


class YieldResponse(CamelModel):
    governorate: str
    season: int
    # With the trained model: national production of Tunisia (scope NATIONAL), see the M3 README.
    regional_production_tonnes: float
    kg_per_tree: float | None = None
    parcel_estimate_kg: float | None = None
    parcel_low_kg: float | None = None
    parcel_high_kg: float | None = None
    model_version: str
    mock: bool
    # Additive fields (the Spring DTO ignores unknown fields).
    scope: Literal["NATIONAL", "REGIONAL"] = "REGIONAL"
    observed: bool = False  # true: the production of this season is already published by FAOSTAT
