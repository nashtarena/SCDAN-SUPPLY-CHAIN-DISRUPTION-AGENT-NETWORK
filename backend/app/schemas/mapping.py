from pydantic import BaseModel, Field


class NodeImpact(BaseModel):
    """One node-to-disruption mapping, as decided by the Mapping Agent (LLM)."""

    node_id: str = Field(description="The id of the impacted supply chain node (Node.id).")
    node_name: str = Field(description="The name of the impacted node, for readability.")
    disruption_index: int = Field(
        description="Index (0-based) into the classified disruptions list this node is impacted by."
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence this node is genuinely impacted, 0 to 1."
    )
    reasoning: str = Field(description="One short sentence explaining the match.")


class NodeImpactBatch(BaseModel):
    """Wrapper so the LLM returns all node impacts in one structured response."""

    impacts: list[NodeImpact]