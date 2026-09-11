import uuid
from datetime import datetime
from typing import Optional, Any, Dict
from sqlalchemy import String, Float, Text, DateTime, JSON, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class ExtractionResultModel(Base):
    __tablename__ = "extraction_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    provider: Mapped[str] = mapped_column(String(50), default="MOCK_OCR_V1", nullable=False)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_fields: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    field_confidences: Mapped[Optional[Dict[str, float]]] = mapped_column(JSON, nullable=True)
    structured_fields: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    confidence_category: Mapped[str] = mapped_column(String(20), default="HIGH", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="SUCCESS", nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document: Mapped["DocumentModel"] = relationship("DocumentModel", back_populates="extraction_results")
