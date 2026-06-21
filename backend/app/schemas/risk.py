from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high", "critical"]


class ClassifiedDisruption(BaseModel):
    """Structured output the Risk Analysis Agent (LangChain + ChatGroq) must produce."""

    affected_region: str = Field(description="The region or country affected by the disruption")
    severity: Severity = Field(description="Overall severity level of the disruption")
    estimated_duration_days: int = Field(
        ge=0, description="Estimated number of days the disruption will last"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Model's confidence in this classification, 0 to 1"
    )
    category: str = Field(
        description="Short category label, e.g. 'labor', 'weather', 'geopolitical', 'infrastructure'"
    )


class ClassifiedDisruptionBatch(BaseModel):
    """
    Wrapper so the LLM returns one structured object containing a classification
    for every input signal, in the same order the signals were given.
    """

    items: list[ClassifiedDisruption]