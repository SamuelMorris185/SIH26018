import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import (
    DocumentNotFoundError,
    InvalidStateTransitionError,
    OversizedFileError,
    UnsupportedFileTypeError,
    ForbiddenError,
)
from app.models.document import DocumentModel
from app.schemas.document import DocumentResponse
from app.services.storage_service import storage_service, BaseStorageService
from app.services.audit_service import audit_service

class DocumentService:
    """
    Manages document metadata, physical storage lifecycle, ownership, and state transitions.
    Enforces upload size limits, MIME type validation, and path safety.
    """

    ALLOWED_TRANSITIONS = {
        "UPLOADED": {"PROCESSING", "FAILED"},
        "REGISTERED": {"PROCESSING", "FAILED"},
        "PROCESSING": {"EXTRACTED", "NORMALIZED", "VALIDATED", "FLAGGED", "FAILED"},
        "EXTRACTED": {"NORMALIZED", "VALIDATED", "FLAGGED", "FAILED"},
        "NORMALIZED": {"VALIDATED", "FLAGGED", "FAILED"},
        "VALIDATED": {"PROCESSING", "FLAGGED", "FAILED"}, # Allow re-processing
        "FLAGGED": {"PROCESSING", "VALIDATED", "FAILED"},   # Allow review & re-processing
        "FAILED": {"PROCESSING"}                           # Allow retry
    }

    def __init__(self, storage: Optional[BaseStorageService] = None):
        self.storage = storage or storage_service

    def validate_file_upload(self, file_name: str, mime_type: str, file_bytes: bytes) -> None:
        """
        Validates file size, MIME type, and extension against security configuration.
        """
        # 1. File size check
        file_size = len(file_bytes)
        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise OversizedFileError(file_size, settings.MAX_UPLOAD_SIZE_BYTES)

        # 2. Extension check
        extension = Path(file_name).suffix.lower()
        if extension and extension not in settings.ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(extension, settings.ALLOWED_EXTENSIONS)

        # 3. MIME type check
        clean_mime = (mime_type or "application/octet-stream").lower().split(";")[0].strip()
        if clean_mime not in settings.ALLOWED_MIME_TYPES:
            raise UnsupportedFileTypeError(clean_mime, settings.ALLOWED_MIME_TYPES)

    def check_document_access(self, doc: DocumentModel, user: Optional[Any] = None) -> None:
        """
        Enforces resource-level ownership.
        Admins, Reviewers, and Viewers can access all records.
        Operators can access their own uploads or unassigned documents.
        """
        if not user:
            return
        user_role = getattr(user, "role", None)
        user_id = getattr(user, "id", None)
        
        if user_role == "OPERATOR" and doc.created_by is not None:
            if doc.created_by != user_id:
                raise ForbiddenError("You do not have permission to access or modify this document.")

    async def register_document(
        self,
        session: AsyncSession,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
        doc_type: str = "JAMABANDI",
        metadata: Optional[Dict[str, Any]] = None,
        created_by: Optional[uuid.UUID] = None
    ) -> DocumentModel:
        """
        Validates, saves to storage, and persists Document entity in DB with audit logging.
        """
        self.validate_file_upload(file_name, mime_type, file_bytes)

        storage_path, file_size = await self.storage.save_file(file_bytes, file_name, mime_type)
        safe_filename = Path(file_name).name or "uploaded_document"
        
        doc = DocumentModel(
            id=uuid.uuid4(),
            file_name=safe_filename,
            file_path=storage_path,
            mime_type=mime_type,
            file_size_bytes=file_size,
            doc_type=doc_type.upper(),
            status="UPLOADED",
            metadata_json=metadata or {},
            created_by=created_by,
            uploaded_at=datetime.utcnow()
        )
        session.add(doc)
        await session.flush()
        logger.info(f"Registered document {doc.id} ('{safe_filename}', {file_size} bytes)")

        await audit_service.log_event(
            session=session,
            action="DOCUMENT_CREATED",
            entity_type="DOCUMENT",
            actor_user_id=created_by,
            entity_id=doc.id,
            new_state={"status": doc.status, "file_name": safe_filename, "file_size": file_size}
        )

        return doc

    async def get_document(self, session: AsyncSession, document_id: uuid.UUID) -> DocumentModel:
        """Fetches document by ID or raises DocumentNotFoundError."""
        result = await session.execute(select(DocumentModel).where(DocumentModel.id == document_id))
        doc = result.scalars().first()
        if not doc:
            raise DocumentNotFoundError(document_id)
        return doc

    async def list_documents(
        self,
        session: AsyncSession,
        status_filter: Optional[str] = None,
        doc_type_filter: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[int, List[DocumentModel]]:
        """Retrieves paginated documents with optional status and doc_type filters."""
        query = select(DocumentModel)

        if status_filter:
            query = query.where(DocumentModel.status == status_filter.upper())
        if doc_type_filter:
            query = query.where(DocumentModel.doc_type == doc_type_filter.upper())

        count_query = select(func.count(DocumentModel.id))
        if status_filter:
            count_query = count_query.where(DocumentModel.status == status_filter.upper())
        if doc_type_filter:
            count_query = count_query.where(DocumentModel.doc_type == doc_type_filter.upper())
            
        total_res = await session.execute(count_query)
        total = total_res.scalar_one()

        offset = (page - 1) * limit
        records_res = await session.execute(
            query.order_by(desc(DocumentModel.uploaded_at)).offset(offset).limit(limit)
        )
        documents = list(records_res.scalars().all())

        return total, documents

    async def update_status(
        self,
        session: AsyncSession,
        document_id: uuid.UUID,
        new_status: str,
        processed_at: Optional[datetime] = None
    ) -> DocumentModel:
        """Updates document processing status with state transition validation."""
        doc = await self.get_document(session, document_id)
        current = doc.status.upper()
        target = new_status.upper()

        if target != current:
            allowed = self.ALLOWED_TRANSITIONS.get(current, set())
            if target not in allowed:
                raise InvalidStateTransitionError(current, target, entity_name="Document")
            
            doc.status = target
            if processed_at or target in {"EXTRACTED", "VALIDATED", "FLAGGED"}:
                doc.processed_at = processed_at or datetime.utcnow()
            
            await session.flush()
            logger.info(f"Document {doc.id} transitioned from {current} to {target}")

            # Audit event
            audit_action = "DOCUMENT_PROCESSED" if target in {"EXTRACTED", "VALIDATED"} else (
                "DOCUMENT_PROCESSING_FAILED" if target == "FAILED" else "DOCUMENT_UPDATED"
            )
            await audit_service.log_event(
                session=session,
                action=audit_action,
                entity_type="DOCUMENT",
                actor_user_id=doc.created_by,
                entity_id=doc.id,
                previous_state={"status": current},
                new_state={"status": target}
            )

        return doc

    def to_response_dto(self, doc: DocumentModel) -> DocumentResponse:
        """
        Converts internal DocumentModel into safe DocumentResponse DTO,
        excluding internal absolute server file paths.
        """
        storage_key = self.storage.get_storage_key(doc.file_path) if hasattr(self.storage, "get_storage_key") else Path(doc.file_path).name
        return DocumentResponse(
            id=doc.id,
            file_name=doc.file_name,
            mime_type=doc.mime_type,
            file_size_bytes=doc.file_size_bytes,
            doc_type=doc.doc_type,
            status=doc.status,
            storage_key=storage_key,
            created_by=doc.created_by,
            metadata_json=doc.metadata_json,
            uploaded_at=doc.uploaded_at,
            processed_at=doc.processed_at
        )

# Global default instance
document_service = DocumentService()
