import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Float, Integer, Text, DateTime, JSON, ForeignKey, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.land_record import LandRecordModel

class RecordComparisonModel(Base):
    __tablename__ = "record_comparisons"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("land_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    compared_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("land_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    match_type: Mapped[str] = mapped_column(String(50), default="PARCEL_EXACT_MATCH", nullable=False)
    discrepancy_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    highest_severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="MATCH_FOUND", nullable=False)
    compared_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    record: Mapped["LandRecordModel"] = relationship(
        "LandRecordModel",
        foreign_keys=[record_id],
        back_populates="comparisons"
    )
    compared_record: Mapped["LandRecordModel"] = relationship(
        "LandRecordModel",
        foreign_keys=[compared_record_id]
    )
    discrepancies: Mapped[List["DiscrepancyModel"]] = relationship(
        "DiscrepancyModel",
        back_populates="comparison",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_record_comparisons_pair", "record_id", "compared_record_id"),
    )

class DiscrepancyModel(Base):
    __tablename__ = "discrepancies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("land_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    compared_record_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("land_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    comparison_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("record_comparisons.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    discrepancy_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    field_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conflicting_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="OPEN", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    land_record: Mapped["LandRecordModel"] = relationship(
        "LandRecordModel",
        foreign_keys=[record_id],
        back_populates="discrepancies"
    )
    compared_land_record: Mapped[Optional["LandRecordModel"]] = relationship(
        "LandRecordModel",
        foreign_keys=[compared_record_id]
    )
    comparison: Mapped[Optional["RecordComparisonModel"]] = relationship(
        "RecordComparisonModel",
        back_populates="discrepancies"
    )

    __table_args__ = (
        Index("ix_discrepancies_record_status", "record_id", "status"),
        Index("ix_discrepancies_type_severity", "discrepancy_type", "severity"),
    )
