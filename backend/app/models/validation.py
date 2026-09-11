import uuid
from datetime import datetime
from typing import List, Optional, Any, Dict
from sqlalchemy import String, Boolean, Text, DateTime, JSON, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class ValidationResultModel(Base):
    __tablename__ = "validation_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("land_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_results: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    discrepancy_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    validated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    land_record: Mapped["LandRecordModel"] = relationship("LandRecordModel", back_populates="validation_results")
