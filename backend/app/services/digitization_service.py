import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.exceptions import (
    DocumentNotFoundError,
    MissingFileError,
    DomainException,
    PipelineProcessingError,
)
from app.models.document import DocumentModel
from app.models.extraction import ExtractionResultModel
from app.models.land_record import LandRecordModel
from app.schemas.document import DocumentResponse
from app.schemas.extraction import ExtractionResultResponse
from app.schemas.record import LandRecordResponse, LandRecordCreate, LandRecordUpdate
from app.schemas.validation import ValidationCheckResponse
from app.schemas.pipeline import DigitizationPipelineResult
from app.schemas.discrepancy import ComparisonSummaryResponse

from app.services.storage_service import storage_service, BaseStorageService
from app.services.document_service import document_service, DocumentService
from app.services.extraction.provider import BaseExtractionProvider, MockExtractionProvider
from app.services.extraction.factory import get_extraction_provider
from app.services.normalization_service import NormalizationService
from app.services.validation_service import validation_service, ValidationService
from app.services.land_record_service import land_record_service, LandRecordService
from app.services.comparison_service import comparison_service, ComparisonService
from app.services.audit_service import audit_service

class DigitizationService:
    """
    End-to-End Processing Pipeline Coordinator:
    Document Verification -> Storage Read -> Extraction -> Normalization -> Record Upsert -> Validation -> Discrepancy Detection -> Persistence.
    """

    def __init__(
        self,
        doc_service: Optional[DocumentService] = None,
        extraction_provider: Optional[BaseExtractionProvider] = None,
        val_service: Optional[ValidationService] = None,
        record_service: Optional[LandRecordService] = None,
        storage: Optional[BaseStorageService] = None,
        comp_service: Optional[ComparisonService] = None
    ):
        self.doc_service = doc_service or document_service
        self._extraction_provider = extraction_provider
        self.val_service = val_service or validation_service
        self.record_service = record_service or land_record_service
        self.storage = storage or storage_service
        self.comparison_service = comp_service or comparison_service

    @property
    def extraction_provider(self) -> BaseExtractionProvider:
        return self._extraction_provider or get_extraction_provider()

    @extraction_provider.setter
    def extraction_provider(self, provider: BaseExtractionProvider) -> None:
        self._extraction_provider = provider

    @staticmethod
    async def process_document_extraction(file_name: str, file_bytes: bytes) -> Dict[str, Any]:
        """
        Backward-compatible static method from Phase 1.
        """
        provider = MockExtractionProvider()
        payload = await provider.extract_document_fields(
            document_id=uuid.uuid4(),
            file_bytes=file_bytes,
            file_name=file_name,
            mime_type="application/octet-stream"
        )
        return payload.model_dump()

    async def execute_pipeline(
        self,
        session: AsyncSession,
        document_id: uuid.UUID
    ) -> DigitizationPipelineResult:
        """
        Coordinates full processing on an existing registered document.
        All database operations are atomic within the session transaction.
        Enforces record upsert semantics to prevent orphan duplicates on re-processing.
        """
        doc = await self.doc_service.get_document(session, document_id)
        logger.info(f"Starting digitization pipeline for Document {document_id} ('{doc.file_name}')")

        # Verify physical file existence in storage before initiating workflow
        if hasattr(self.storage, "file_exists") and not self.storage.file_exists(doc.file_path):
            logger.error(f"Document file missing in storage for document {document_id}")
            await self.doc_service.update_status(session, document_id, "FAILED")
            await session.commit()
            raise MissingFileError(doc.file_path)

        try:
            # Stage 1: Transition document to PROCESSING
            doc = await self.doc_service.update_status(session, document_id, "PROCESSING")

            # Stage 2: Read document binary from storage abstraction
            file_bytes = await self.storage.read_file(doc.file_path)

            # Stage 3: Extraction (Pluggable Isolated Provider)
            raw_extraction = await self.extraction_provider.extract_document_fields(
                document_id=doc.id,
                file_bytes=file_bytes,
                file_name=doc.file_name,
                mime_type=doc.mime_type
            )

            # Stage 4: Persist raw ExtractionResultModel with structured fields
            structured_dict = None
            if raw_extraction.structured_fields:
                structured_dict = {
                    k: v.model_dump() for k, v in raw_extraction.structured_fields.items()
                }
            cat_str = (
                raw_extraction.confidence_category.value
                if hasattr(raw_extraction.confidence_category, "value")
                else str(raw_extraction.confidence_category)
            )

            extraction_model = ExtractionResultModel(
                id=uuid.uuid4(),
                document_id=doc.id,
                provider=raw_extraction.provider,
                raw_text=raw_extraction.raw_text,
                extracted_fields=raw_extraction.extracted_fields,
                field_confidences=raw_extraction.field_confidences,
                structured_fields=structured_dict,
                confidence_score=raw_extraction.confidence_score,
                confidence_category=cat_str,
                status=raw_extraction.status,
                extracted_at=datetime.utcnow()
            )
            session.add(extraction_model)
            await session.flush()
            doc = await self.doc_service.update_status(session, document_id, "EXTRACTED")

            # Stage 5: Deterministic Normalization
            normalized_fields = NormalizationService.normalize_record_data(raw_extraction.extracted_fields)

            # Stage 6: Record Upsert (Update existing record if re-processing, else create new)
            existing_records = await self.record_service.list_by_document(session, doc.id)
            if existing_records:
                record_model = existing_records[0]
                update_payload = LandRecordUpdate(
                    state=normalized_fields["state"],
                    district=normalized_fields["district"],
                    tehsil=normalized_fields["tehsil"],
                    village=normalized_fields["village"],
                    khasra_number=normalized_fields["khasra_number"],
                    khata_number=normalized_fields["khata_number"],
                    area_in_hectares=normalized_fields["area_in_hectares"],
                    land_classification=normalized_fields["land_classification"],
                    owner_name=normalized_fields.get("owner_name"),
                    co_owners=normalized_fields.get("co_owners"),
                    patta_number=normalized_fields.get("patta_number"),
                    registration_number=normalized_fields.get("registration_number"),
                    mutation_number=normalized_fields.get("mutation_number"),
                    document_date=normalized_fields.get("document_date"),
                    status="NORMALIZED"
                )
                record_model = await self.record_service.update_record(session, record_model.id, update_payload)
                record_model.confidence_score = raw_extraction.confidence_score
                await session.flush()
                logger.info(f"Updated existing land record {record_model.id} for document {doc.id}")
                await audit_service.log_event(
                    session=session,
                    action="RECORD_UPDATED",
                    entity_type="LAND_RECORD",
                    actor_user_id=doc.created_by,
                    entity_id=record_model.id,
                    new_state={"status": record_model.status, "khasra": record_model.khasra_number}
                )
            else:
                record_create = LandRecordCreate(
                    document_id=doc.id,
                    created_by=doc.created_by,
                    state=normalized_fields["state"],
                    district=normalized_fields["district"],
                    tehsil=normalized_fields["tehsil"],
                    village=normalized_fields["village"],
                    khasra_number=normalized_fields["khasra_number"],
                    khata_number=normalized_fields["khata_number"],
                    area_in_hectares=normalized_fields["area_in_hectares"],
                    land_classification=normalized_fields["land_classification"],
                    owner_name=normalized_fields.get("owner_name"),
                    co_owners=normalized_fields.get("co_owners"),
                    patta_number=normalized_fields.get("patta_number"),
                    registration_number=normalized_fields.get("registration_number"),
                    mutation_number=normalized_fields.get("mutation_number"),
                    document_date=normalized_fields.get("document_date"),
                    confidence_score=raw_extraction.confidence_score,
                    status="NORMALIZED",
                    review_status="PENDING_REVIEW"
                )
                record_model = await self.record_service.create_record(session, record_create)
                logger.info(f"Created new land record {record_model.id} for document {doc.id}")
                await audit_service.log_event(
                    session=session,
                    action="RECORD_CREATED",
                    entity_type="LAND_RECORD",
                    actor_user_id=doc.created_by,
                    entity_id=record_model.id,
                    new_state={"status": record_model.status, "khasra": record_model.khasra_number}
                )

            # Stage 7: Validation Engine Check & Persistence
            record_dict = {
                "state": record_model.state,
                "district": record_model.district,
                "tehsil": record_model.tehsil,
                "village": record_model.village,
                "khasra_number": record_model.khasra_number,
                "khata_number": record_model.khata_number,
                "area_in_hectares": float(record_model.area_in_hectares),
                "land_classification": record_model.land_classification,
                "confidence_score": record_model.confidence_score
            }
            validation_resp = await self.val_service.validate_and_persist(
                record_id=record_model.id,
                record_data=record_dict,
                session=session
            )

            # Audit event for record validation
            val_audit_action = "RECORD_VALIDATED" if validation_resp.is_valid else "RECORD_FLAGGED"
            await audit_service.log_event(
                session=session,
                action=val_audit_action,
                entity_type="LAND_RECORD",
                actor_user_id=doc.created_by,
                entity_id=record_model.id,
                new_state={"is_valid": validation_resp.is_valid, "status": record_model.status}
            )

            # Stage 8: Cross-Document Comparison & Discrepancy Detection (Phase 5)
            comparison_summary = await self.comparison_service.compare_record(session, record_model.id)
            if comparison_summary.total_discrepancies > 0:
                await audit_service.log_event(
                    session=session,
                    action="DISCREPANCIES_DETECTED",
                    entity_type="LAND_RECORD",
                    actor_user_id=doc.created_by,
                    entity_id=record_model.id,
                    new_state={
                        "total": comparison_summary.total_discrepancies,
                        "critical": comparison_summary.critical_count,
                        "high": comparison_summary.high_count,
                        "highest_severity": comparison_summary.highest_severity
                    }
                )

            # Refresh record status in case comparison marked it FLAGGED
            await session.refresh(record_model)

            # Stage 9: Update Document final status (VALIDATED vs FLAGGED)
            is_record_flagged = (
                not validation_resp.is_valid
                or record_model.status == "FLAGGED"
                or (comparison_summary.highest_severity in ("CRITICAL", "HIGH"))
            )
            final_doc_status = "FLAGGED" if is_record_flagged else "VALIDATED"
            doc = await self.doc_service.update_status(session, document_id, final_doc_status)

            summary = (
                f"Successfully processed document {doc.id}. "
                f"Record ID: {record_model.id} (Status: {record_model.status}). "
                f"Validation: {'PASSED' if validation_resp.is_valid else 'FLAGGED'}. "
                f"Discrepancies: {comparison_summary.total_discrepancies} detected "
                f"({comparison_summary.critical_count} critical, {comparison_summary.high_count} high)."
            )
            logger.info(summary)

            return DigitizationPipelineResult(
                document=self.doc_service.to_response_dto(doc),
                extraction=ExtractionResultResponse.model_validate(extraction_model),
                records=[LandRecordResponse.model_validate(record_model)],
                validations=[validation_resp],
                discrepancies=comparison_summary,
                summary=summary
            )

        except DomainException as de:
            logger.warning(f"Domain error during pipeline processing for document {document_id}: {de.message}")
            try:
                await self.doc_service.update_status(session, document_id, "FAILED")
                await session.commit()
            except Exception:
                pass
            raise de
        except Exception as exc:
            logger.error(f"Unexpected pipeline failure for document {document_id}: {str(exc)}", exc_info=True)
            try:
                await self.doc_service.update_status(session, document_id, "FAILED")
                await session.commit()
            except Exception:
                pass
            raise PipelineProcessingError(str(exc))

    async def upload_and_process(
        self,
        session: AsyncSession,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
        doc_type: str = "JAMABANDI",
        metadata: Optional[Dict[str, Any]] = None
    ) -> DigitizationPipelineResult:
        """
        Convenience one-step method: registers document and immediately runs the full pipeline.
        """
        doc = await self.doc_service.register_document(
            session=session,
            file_name=file_name,
            mime_type=mime_type,
            file_bytes=file_bytes,
            doc_type=doc_type,
            metadata=metadata
        )
        return await self.execute_pipeline(session, doc.id)

# Global default instance
digitization_service = DigitizationService()
