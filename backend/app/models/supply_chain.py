import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPk
from app.models.user import User

class SupplyChain(Base, TimestampMixin):
    __tablename__ = "supply_chains"

    id: Mapped[uuid.UUID] = UUIDPk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    nodes: Mapped[list["SupplyChainNode"]] = relationship(
        back_populates="supply_chain", cascade="all, delete-orphan"
    )
    edges: Mapped[list["SupplyChainEdge"]] = relationship(
        back_populates="supply_chain", cascade="all, delete-orphan"
    )
    owner: Mapped["User"] = relationship(back_populates="supply_chains")


class SupplyChainNode(Base, TimestampMixin):
    __tablename__ = "supply_chain_nodes"

    id: Mapped[uuid.UUID] = UUIDPk()
    supply_chain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supply_chains.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # type: e.g. "supplier", "factory", "port", "warehouse", "distributor"
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    region: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    supply_chain: Mapped["SupplyChain"] = relationship(back_populates="nodes")


class SupplyChainEdge(Base, TimestampMixin):
    __tablename__ = "supply_chain_edges"

    id: Mapped[uuid.UUID] = UUIDPk()
    supply_chain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supply_chains.id"), nullable=False
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supply_chain_nodes.id"), nullable=False
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supply_chain_nodes.id"), nullable=False
    )
    # e.g. "ship", "truck", "rail", "air"
    transport_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)

    supply_chain: Mapped["SupplyChain"] = relationship(back_populates="edges")
