import uuid
from typing import Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.core.logging import logger

class DomainException(Exception):
    """Base domain exception."""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details

class EntityNotFoundError(DomainException):
    def __init__(self, entity_name: str, entity_id: Any):
        super().__init__(
            message=f"{entity_name} with identifier '{entity_id}' not found.",
            status_code=status.HTTP_404_NOT_FOUND
        )

class DocumentNotFoundError(EntityNotFoundError):
    def __init__(self, document_id: uuid.UUID):
        super().__init__("Document", document_id)

class RecordNotFoundError(EntityNotFoundError):
    def __init__(self, record_id: uuid.UUID):
        super().__init__("Land record", record_id)

class ExtractionNotFoundError(EntityNotFoundError):
    def __init__(self, extraction_id: uuid.UUID):
        super().__init__("Extraction result", extraction_id)

class UserNotFoundError(EntityNotFoundError):
    def __init__(self, user_id: Any):
        super().__init__("User", user_id)

class UserAlreadyExistsError(DomainException):
    def __init__(self, email: str):
        super().__init__(
            message=f"User with email '{email}' already exists.",
            status_code=status.HTTP_409_CONFLICT
        )

class AuthenticationError(DomainException):
    def __init__(self, message: str = "Invalid credentials or unauthenticated request."):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
        self.headers = {"WWW-Authenticate": "Bearer"}

class ForbiddenError(DomainException):
    def __init__(self, message: str = "Insufficient permissions to perform this action."):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )

class InvalidStateTransitionError(DomainException):
    def __init__(self, current_status: str, attempted_status: str, entity_name: str = "Entity"):
        super().__init__(
            message=f"Invalid state transition for {entity_name}: cannot transition from '{current_status}' to '{attempted_status}'.",
            status_code=status.HTTP_409_CONFLICT
        )

class OversizedFileError(DomainException):
    def __init__(self, size_bytes: int, max_bytes: int):
        max_mb = max_bytes / (1024 * 1024)
        current_mb = size_bytes / (1024 * 1024)
        super().__init__(
            message=f"File size ({current_mb:.2f}MB) exceeds maximum permitted upload limit of {max_mb:.1f}MB.",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        )

class UnsupportedFileTypeError(DomainException):
    def __init__(self, mime_type: str, allowed_types: list):
        super().__init__(
            message=f"Unsupported file format '{mime_type}'. Supported formats: {', '.join(allowed_types)}.",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        )

class MissingFileError(DomainException):
    def __init__(self, file_path: str):
        super().__init__(
            message=f"Physical document file could not be located in storage.",
            status_code=status.HTTP_404_NOT_FOUND
        )

class ExtractionProcessingError(DomainException):
    def __init__(self, message: str):
        super().__init__(
            message=f"Document extraction failed: {message}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

class PipelineProcessingError(DomainException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=f"Pipeline processing failed: {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )

class OCREngineUnavailableError(DomainException):
    def __init__(self, engine_name: str, reason: str):
        super().__init__(
            message=f"OCR engine '{engine_name}' is currently unavailable: {reason}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"engine": engine_name, "reason": reason}
        )

class DiscrepancyNotFoundError(EntityNotFoundError):
    def __init__(self, discrepancy_id: uuid.UUID):
        super().__init__("Discrepancy", discrepancy_id)

class JobNotFoundError(EntityNotFoundError):
    def __init__(self, job_id: Any):
        super().__init__("Processing job", job_id)

class DuplicateProcessingError(DomainException):
    def __init__(self, document_id: Any, active_job_id: Optional[Any] = None):
        super().__init__(
            message=f"Document '{document_id}' is already being processed by active job '{active_job_id}'.",
            status_code=status.HTTP_409_CONFLICT,
            details={"document_id": str(document_id), "active_job_id": str(active_job_id) if active_job_id else None}
        )

class JobNotRetryableError(DomainException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )

class ComparisonError(DomainException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=f"Record comparison error: {message}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    logger.warning(f"Domain error on {request.method} {request.url.path}: {exc.message}")
    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        headers=headers,
        content={
            "status": "error",
            "code": exc.status_code,
            "message": exc.message,
            "details": exc.details
        }
    )

async def database_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Database error encountered on {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "error",
            "code": status.HTTP_503_SERVICE_UNAVAILABLE,
            "message": "Database service is currently unavailable. Please verify that PostgreSQL is running and accessible.",
            "details": None
        }
    )
