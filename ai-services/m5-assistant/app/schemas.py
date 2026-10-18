from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

Intent = Literal[
    "maladie",
    "irrigation",
    "meteo_alerte",
    "recolte",
    "prix_vente",
    "comptage",
    "conseil_general",
    "salutation",
    "hors_sujet",
]


class CamelModel(BaseModel):
    """snake_case in Python, camelCase in JSON (the contract with the Spring backend)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class IntentRequest(CamelModel):
    text: str = Field(min_length=1, max_length=500, examples=["9adech nesgi zitouni had el jem3a?"])

    @field_validator("text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class Candidate(CamelModel):
    intent: Intent
    score: float


class Entities(CamelModel):
    gouvernorat: str | None = None


class IntentResponse(CamelModel):
    intent: Intent  # best guess, even when clarify is true
    confidence: float
    clarify: bool
    question: str | None = None  # question to ask the farmer when clarify is true
    candidates: list[Candidate]  # top 3, best first
    models_agree: bool  # TF-IDF and SetFit have the same top intent
    entities: Entities
    model_version: str
    mock: bool  # true = keyword fallback, the trained ensemble is not loaded


# ---- POST /answer: the LLM writes the reply from the facts gathered by the backend ----


class Fact(CamelModel):
    source: str = Field(examples=["M2"])  # module that produced the data
    mock: bool = False
    data: dict


class ParcelInfo(CamelModel):
    name: str | None = None
    governorate: str | None = None
    tree_count: int | None = None
    area_ha: float | None = None
    variety: str | None = None
    irrigated: bool | None = None


class AnswerRequest(CamelModel):
    question: str = Field(min_length=1, max_length=500)
    intent: Intent
    facts: list[Fact] = Field(default_factory=list, max_length=10)
    parcel: ParcelInfo | None = None
    draft: str | None = Field(default=None, max_length=2000)  # template answer, used as a base


class AnswerResponse(CamelModel):
    answer: str
    provider: str
    model: str
    latency_ms: int
