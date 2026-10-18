from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """snake_case in Python, camelCase in JSON (the contract with the Spring backend)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Box(CamelModel):
    """Pixel coordinates in the uploaded image (top-left corner + size)."""

    x: float
    y: float
    width: float
    height: float
    confidence: float


class TreeCountResponse(CamelModel):
    tree_count: int
    boxes: list[Box]
    annotated_image_base64: str | None = None  # PNG with the boxes drawn
    model_version: str
    mock: bool
