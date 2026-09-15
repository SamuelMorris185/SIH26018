import uuid
from datetime import datetime, timezone
import jwt
import pytest
from pydantic import ValidationError
from sqlalchemy import select, func, text

from app.core.config import Settings, settings
from app.core.exceptions import AuthenticationError, PipelineProcessingError
from app.core.security import decode_access_token
from app.models.extraction import ExtractionResultModel
from app.models.land_record import LandRecordModel
from app.schemas.extraction import ExtractionResultResponse
from app.schemas.user import UserCreate
from app.services.digitization_service import digitization_service
from app.services.document_service import document_service
from app.services.extraction.tesseract_provider import TesseractOCRProvider
from app.services.gis_service import gis_service
from app.services.normalization_service import NormalizationService
from scripts.seed_support import require_migrations


@pytest.mark.parametrize("password", ["a" * 73, "अ" * 25])
def test_bcrypt_rejects_overlong_utf8_passwords(password):
    with pytest.raises(ValidationError, match="72 UTF-8 bytes"):
        UserCreate(email="test@example.com", full_name="Test", password=password)


@pytest.mark.parametrize("claim", ["sub", "iat", "exp"])
def test_jwt_requires_security_claims(claim):
    payload = {"sub": str(uuid.uuid4()), "iat": datetime.now(timezone.utc), "exp": 9999999999}
    payload.pop(claim)
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(AuthenticationError):
        decode_access_token(token)


def test_production_rejects_demo_secret_and_unknown_ocr():
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None, APP_ENV="production", JWT_SECRET_KEY="dev_shared_secret")
    with pytest.raises(ValidationError, match="OCR_ENGINE"):
        Settings(_env_file=None, OCR_ENGINE="typo")


@pytest.mark.parametrize("raw,expected", [("2 acres", 0.8094), ("10,000 sq.m", 1.0), ("2 bigha", 0.0), (float("nan"), 0.0)])
def test_area_units_are_not_silently_relabelled(raw, expected):
    assert NormalizationService.normalize_area(raw) == expected


@pytest.mark.parametrize("geo", [
    {"type": "Point", "coordinates": [181, 91]},
    {"type": "Point", "coordinates": [0, float("nan")]},
    {"type": "Polygon", "coordinates": []},
    {"type": "MultiPolygon", "coordinates": [[]]},
])
def test_invalid_geometry_is_rejected(geo):
    assert not gis_service.validate_geometry_payload(None, None, geo).is_valid


def test_geometry_rejects_wrong_crs_and_partial_centroid():
    assert not gis_service.validate_geometry_payload(10, None, None).is_valid
    assert not gis_service.validate_geometry_payload(10, 20, None, "EPSG:3857").is_valid


def test_ocr_does_not_invent_missing_state():
    fields, _, _, _ = TesseractOCRProvider()._parse_land_record_text(
        "District: Jaipur\nVillage: Rampura\nKhasra No: 104/2", 0.95
    )
    assert fields["state"] == ""


def test_stored_extraction_restores_low_confidence_fields():
    result = ExtractionResultResponse(
        id=uuid.uuid4(), document_id=uuid.uuid4(), extracted_fields={},
        field_confidences={"owner_name": 0.4, "state": 0.95}, extracted_at=datetime.utcnow(),
    )
    assert result.low_confidence_fields == ["owner_name"]


async def test_seed_refuses_unmigrated_schema(db_session):
    with pytest.raises(RuntimeError, match="alembic upgrade head"):
        await require_migrations(db_session)


async def test_pipeline_rolls_back_partial_data_before_failure(db_session, monkeypatch):
    doc = await document_service.register_document(db_session, "rollback.pdf", "application/pdf", b"test")
    document_id = doc.id
    await db_session.commit()

    async def fail_comparison(session, record_id):
        await session.execute(text("SELECT * FROM deliberately_missing_audit_table"))

    monkeypatch.setattr(digitization_service.comparison_service, "compare_record", fail_comparison)
    with pytest.raises(PipelineProcessingError):
        await digitization_service.execute_pipeline(db_session, document_id)
    for model in (ExtractionResultModel, LandRecordModel):
        assert (await db_session.execute(select(func.count()).select_from(model))).scalar_one() == 0
    assert (await document_service.get_document(db_session, document_id)).status == "FAILED"
