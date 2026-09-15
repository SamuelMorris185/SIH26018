from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.config import settings
from app.db.session import get_db_session
from app.models.land_record import LandRecordModel
from app.models.document import DocumentModel
from app.models.discrepancy import DiscrepancyModel
from app.schemas.health import OCRStatusResponse, DashboardStatsResponse
from app.services.extraction.factory import get_extraction_provider
from app.services.extraction.tesseract_provider import TesseractOCRProvider
from app.api.dependencies.auth import get_current_user
from app.models.user import UserModel

router = APIRouter(prefix="/system", tags=["System & OCR Diagnostics"])

@router.get("/ocr-status", response_model=OCRStatusResponse)
async def get_ocr_status():
    """
    Returns non-sensitive health, configuration, and runtime status for the active OCR engine.
    Indicates whether real Tesseract OCR or Mock provider is active, binary availability,
    engine version, and supported offline language models.
    """
    selected_engine = settings.OCR_ENGINE.strip().upper()
    provider = get_extraction_provider()
    
    version = None
    languages = []
    
    if isinstance(provider, TesseractOCRProvider):
        info = provider.get_engine_status()
        version = info.get("version")
        languages = info.get("supported_languages", [])
        is_available = info.get("available", False)
    else:
        is_available = provider.is_available
        version = "1.0.0-mock"
        languages = ["eng", "hin"]

    return OCRStatusResponse(
        selected_engine=selected_engine,
        available=is_available,
        provider_name=provider.provider_name,
        engine_version=version,
        supported_languages=languages,
        offline_operational=True
    )

@router.get("/dashboard-stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(session: AsyncSession = Depends(get_db_session), current_user: UserModel = Depends(get_current_user)):
    """
    Returns live aggregated system statistics across land records, processed documents,
    review queues, and discrepancies directly from database counts.
    """
    # Total records
    res_total = await session.execute(select(func.count(LandRecordModel.id)))
    total_records = res_total.scalar_one() or 0

    # Documents processed
    res_docs = await session.execute(
        select(func.count(DocumentModel.id)).where(DocumentModel.status.in_(["VALIDATED", "FLAGGED"]))
    )
    docs_processed = res_docs.scalar_one() or 0

    # Records awaiting review
    res_pending = await session.execute(
        select(func.count(LandRecordModel.id)).where(
            LandRecordModel.review_status.in_(["PENDING_REVIEW", "IN_REVIEW"])
        )
    )
    records_awaiting_review = res_pending.scalar_one() or 0

    # Validated records
    res_val = await session.execute(
        select(func.count(LandRecordModel.id)).where(LandRecordModel.status == "VALIDATED")
    )
    validated_records = res_val.scalar_one() or 0

    # Flagged records
    res_flagged = await session.execute(
        select(func.count(LandRecordModel.id)).where(LandRecordModel.status == "FLAGGED")
    )
    flagged_records = res_flagged.scalar_one() or 0

    # Open discrepancies
    res_disc = await session.execute(
        select(func.count(DiscrepancyModel.id)).where(DiscrepancyModel.status == "OPEN")
    )
    open_discrepancies = res_disc.scalar_one() or 0

    # Low-confidence records
    res_low_conf = await session.execute(
        select(func.count(LandRecordModel.id)).where(LandRecordModel.confidence_score < 0.60)
    )
    low_confidence_records = res_low_conf.scalar_one() or 0

    # Approved records
    res_app = await session.execute(
        select(func.count(LandRecordModel.id)).where(LandRecordModel.review_status == "APPROVED")
    )
    approved_records = res_app.scalar_one() or 0

    # Rejected records
    res_rej = await session.execute(
        select(func.count(LandRecordModel.id)).where(LandRecordModel.review_status == "REJECTED")
    )
    rejected_records = res_rej.scalar_one() or 0

    return DashboardStatsResponse(
        total_records=total_records,
        documents_processed=docs_processed,
        records_awaiting_review=records_awaiting_review,
        validated_records=validated_records,
        flagged_records=flagged_records,
        open_discrepancies=open_discrepancies,
        low_confidence_records=low_confidence_records,
        approved_records=approved_records,
        rejected_records=rejected_records,
    )
