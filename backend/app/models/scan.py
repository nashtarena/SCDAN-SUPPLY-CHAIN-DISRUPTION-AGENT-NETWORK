import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPk


class ScanResult(Base, TimestampMixin):
    __tablename__ = "scan_results"

    id: Mapped[uuid.UUID] = UUIDPk()
    supply_chain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supply_chains.id"), nullable=False
    )
    # pending -> running -> completed | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    timing: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="scan_result", cascade="all, delete-orphan"
    )


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = UUIDPk()
    scan_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scan_results.id"), nullable=False
    )
    supply_chain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supply_chains.id"), nullable=False
    )
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supply_chain_nodes.id"), nullable=True
    )

    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    region: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    scan_result: Mapped["ScanResult"] = relationship(back_populates="alerts")