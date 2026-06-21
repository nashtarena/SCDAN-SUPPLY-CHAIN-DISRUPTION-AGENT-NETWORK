from datetime import datetime, timezone

from pydantic import BaseModel, Field


class DisruptionSignal(BaseModel):
    """Standard normalized output every ingestion agent must produce."""

    source: str  # "news" | "weather" | "disaster"
    region: str
    description: str
    severity_hint: str  # "low" | "medium" | "high" | "critical" (agent's rough guess)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_data: dict = Field(default_factory=dict)