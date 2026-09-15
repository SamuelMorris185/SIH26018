import uuid
from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Float, DateTime, JSON, ForeignKey, Index, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.land_record import LandRecordModel

class ParcelLocationModel(Base):
    __tablename__ = "parcel_locations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("land_records.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    boundary_geojson: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    coordinate_reference_system: Mapped[str] = mapped_column(String(50), default="EPSG:4326", nullable=False)
    geometry_validation_status: Mapped[str] = mapped_column(String(50), default="VALID", nullable=False)
    map_source: Mapped[str] = mapped_column(String(100), default="CADASTRAL_SURVEY", nullable=False)
    location_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    land_record: Mapped["LandRecordModel"] = relationship(
        "LandRecordModel",
        back_populates="parcel_location"
    )

    __table_args__ = (
        UniqueConstraint("record_id", name="uq_parcel_locations_record_id"),
        Index("ix_parcel_locations_coords", "latitude", "longitude"),
    )
