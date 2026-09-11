import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Numeric, Float, DateTime, ForeignKey, Index, Uuid, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import DocumentModel
    from app.models.validation import ValidationResultModel
    from app.models.discrepancy import DiscrepancyModel, RecordComparisonModel
    from app.models.parcel_location import ParcelLocationModel


class LandRecordModel(Base):
    __tablename__ = "land_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    tehsil: Mapped[str] = mapped_column(String(100), nullable=False)
    village: Mapped[str] = mapped_column(String(100), nullable=False)
    khasra_number: Mapped[str] = mapped_column(String(50), nullable=False)
    khata_number: Mapped[str] = mapped_column(String(50), nullable=False)
    area_in_hectares: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    land_classification: Mapped[str] = mapped_column(String(100), nullable=True, default="Agricultural")
    
    # Structured Land Record Owner & Legal Identifiers (Phase 5)
    owner_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    co_owners: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    patta_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    registration_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mutation_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    document_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(50), default="EXTRACTED", nullable=False, index=True)
    
    # Human Review Workflow Fields
    review_status: Mapped[str] = mapped_column(String(50), default="PENDING_REVIEW", nullable=False, index=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    document: Mapped[Optional["DocumentModel"]] = relationship(
        "DocumentModel",
        back_populates="land_records"
    )
    validation_results: Mapped[List["ValidationResultModel"]] = relationship(
        "ValidationResultModel",
        back_populates="land_record",
        cascade="all, delete-orphan",
        order_by="desc(ValidationResultModel.validated_at)"
    )
    discrepancies: Mapped[List["DiscrepancyModel"]] = relationship(
        "DiscrepancyModel",
        foreign_keys="[DiscrepancyModel.record_id]",
        back_populates="land_record",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(DiscrepancyModel.created_at)"
    )
    comparisons: Mapped[List["RecordComparisonModel"]] = relationship(
        "RecordComparisonModel",
        foreign_keys="[RecordComparisonModel.record_id]",
        back_populates="record",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(RecordComparisonModel.compared_at)"
    )
    parcel_location: Mapped[Optional["ParcelLocationModel"]] = relationship(
        "ParcelLocationModel",
        uselist=False,
        back_populates="land_record",
        cascade="all, delete-orphan",
        lazy="joined"
    )

    __table_args__ = (

        Index("ix_land_records_location", "state", "district", "tehsil", "village"),
        Index("ix_land_records_khasra_khata", "khasra_number", "khata_number"),
    )
