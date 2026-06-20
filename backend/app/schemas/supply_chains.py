import uuid

from pydantic import BaseModel, ConfigDict, Field


# ---------- SupplyChain ----------

class SupplyChainCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class SupplyChainUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class SupplyChainOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str | None


class SupplyChainDetailOut(SupplyChainOut):
    nodes: list["NodeOut"] = []
    edges: list["EdgeOut"] = []


# ---------- Node ----------

class NodeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(min_length=1, max_length=50)
    region: str = Field(min_length=1, max_length=255)
    latitude: float | None = None
    longitude: float | None = None


class NodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supply_chain_id: uuid.UUID
    name: str
    type: str
    region: str
    latitude: float | None
    longitude: float | None


# ---------- Edge ----------

class EdgeCreate(BaseModel):
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    transport_mode: str | None = None


class EdgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supply_chain_id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    transport_mode: str | None


SupplyChainDetailOut.model_rebuild()