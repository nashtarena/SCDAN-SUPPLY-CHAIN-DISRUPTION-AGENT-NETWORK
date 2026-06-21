import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScanTriggerRequest(BaseModel):
    supply_chain_id: uuid.UUID


class ScanQueuedOut(BaseModel):
    scan_result_id: uuid.UUID
    status: str


class ScanResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supply_chain_id: uuid.UUID
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    timing: dict | None
    error_message: str | None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scan_result_id: uuid.UUID
    supply_chain_id: uuid.UUID
    node_id: uuid.UUID | None
    severity: str
    category: str
    region: str
    message: str
    created_at: datetime