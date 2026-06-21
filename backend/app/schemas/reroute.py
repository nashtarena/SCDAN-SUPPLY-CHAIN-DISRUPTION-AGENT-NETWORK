from pydantic import BaseModel, Field


class RerouteSuggestion(BaseModel):
    """Structured output the Reroute Agent (LangChain + ChatGroq) must produce, per impacted node."""

    node_id: str
    node_name: str
    suggestion: str = Field(description="Short, human-readable rerouting recommendation.")
    recommended_alternative_node_ids: list[str] = Field(
        default_factory=list, description="Subset of the given alternative node ids actually recommended."
    )
