import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from sqlalchemy import String, Integer, DateTime, JSON, Uuid, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), default="JAMABANDI", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="UPLOADED", nullable=False, index=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    land_records: Mapped[List["LandRecordModel"]] = relationship(
        "LandRecordModel",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    extraction_results: Mapped[List["ExtractionResultModel"]] = relationship(
        "ExtractionResultModel",
        back_populates="document",
        cascade="all, delete-orphan"
    )
