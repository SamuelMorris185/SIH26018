import io
import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.land_record import LandRecordModel
from app.models.document import DocumentModel
from app.models.extraction import ExtractionResultModel
from app.models.validation import ValidationResultModel
from app.models.discrepancy import DiscrepancyModel
from app.models.parcel_location import ParcelLocationModel
from app.models.user import UserModel
from app.models.audit_log import AuditLogModel
from app.core.security import get_password_hash, create_access_token
from tests.conftest import TestAsyncSessionLocal


def create_test_users():
    admin = UserModel(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        email="admin_report@sih.gov.in",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Report Administrator",
        role="ADMIN",
        is_active=True,
        created_at=datetime.utcnow()
    )
    reviewer = UserModel(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        email="reviewer_report@sih.gov.in",
        hashed_password=get_password_hash("ReviewerPass123!"),
        full_name="Report Reviewer",
        role="REVIEWER",
        is_active=True,
        created_at=datetime.utcnow()
    )
    viewer = UserModel(
        id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        email="viewer_report@sih.gov.in",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Report Viewer",
        role="VIEWER",
        is_active=True,
        created_at=datetime.utcnow()
    )
    operator_a = UserModel(
        id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        email="operator_report_a@sih.gov.in",
        hashed_password=get_password_hash("OperatorPass123!"),
        full_name="Report Operator A",
        role="OPERATOR",
        is_active=True,
        created_at=datetime.utcnow()
    )
    operator_b = UserModel(
        id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        email="operator_report_b@sih.gov.in",
        hashed_password=get_password_hash("OperatorPass123!"),
        full_name="Report Operator B",
        role="OPERATOR",
        is_active=True,
        created_at=datetime.utcnow()
    )
    return admin, reviewer, viewer, operator_a, operator_b


@pytest.mark.asyncio
async def test_authorized_report_generation_as_admin(client: TestClient, db_session: AsyncSession):
    """Verifies that an authorized user can generate a valid PDF Verification Report with proper headers."""
    record_id = uuid.uuid4()
    record = LandRecordModel(
        id=record_id,
        state="Rajasthan",
        district="Jaipur",
        tehsil="Sanganer",
        village="Rampura",
        khasra_number="101/A",
        khata_number="45",
        area_in_hectares=2.5000,
        land_classification="Agricultural",
        owner_name="Ramesh Sharma",
        confidence_score=0.92,
        status="VALIDATED",
        review_status="PENDING_REVIEW",
        created_at=datetime.utcnow()
    )
    db_session.add(record)
    await db_session.commit()

    res = client.get(f"/api/v1/records/{record_id}/verification-report")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in res.headers["content-disposition"]
    assert "verification_report_101_A_" in res.headers["content-disposition"]

    # Verify PDF content integrity
    assert res.content.startswith(b"%PDF-")
    assert len(res.content) > 1500


def test_unauthorized_report_access_401(unauthenticated_client: TestClient):
    """Verifies that requests without authentication tokens receive 401 Unauthorized."""
    random_id = uuid.uuid4()
    res = unauthenticated_client.get(f"/api/v1/records/{random_id}/verification-report")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_operator_ownership_isolation_403(unauthenticated_client: TestClient, db_session: AsyncSession):
    """Verifies resource ownership isolation: Operator B cannot export Operator A's record."""
    admin, reviewer, viewer, op_a, op_b = create_test_users()
    db_session.add_all([admin, reviewer, viewer, op_a, op_b])

    record_id = uuid.uuid4()
    record = LandRecordModel(
        id=record_id,
        created_by=op_a.id,
        state="Rajasthan",
        district="Jaipur",
        tehsil="Sanganer",
        village="Rampura",
        khasra_number="202/B",
        khata_number="50",
        area_in_hectares=1.7500,
        land_classification="Agricultural",
        owner_name="Sita Devi",
        confidence_score=0.95,
        status="VALIDATED",
        review_status="PENDING_REVIEW",
        created_at=datetime.utcnow()
    )
    db_session.add(record)
    await db_session.commit()

    token_b = create_access_token(data={"sub": str(op_b.id), "role": op_b.role})
    res_b = unauthenticated_client.get(
        f"/api/v1/records/{record_id}/verification-report",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res_b.status_code == 403
    assert "permission" in res_b.json()["message"].lower()


@pytest.mark.asyncio
async def test_operator_own_record_access_200(unauthenticated_client: TestClient, db_session: AsyncSession):
    """Verifies that Operator A can export their own record."""
    admin, reviewer, viewer, op_a, op_b = create_test_users()
    db_session.add_all([admin, reviewer, viewer, op_a, op_b])

    record_id = uuid.uuid4()
    record = LandRecordModel(
        id=record_id,
        created_by=op_a.id,
        state="Rajasthan",
        district="Jaipur",
        tehsil="Sanganer",
        village="Rampura",
        khasra_number="303/C",
        khata_number="77",
        area_in_hectares=4.1200,
        land_classification="Agricultural",
        owner_name="Vijay Meena",
        confidence_score=0.88,
        status="VALIDATED",
        review_status="PENDING_REVIEW",
        created_at=datetime.utcnow()
    )
    db_session.add(record)
    await db_session.commit()

    token_a = create_access_token(data={"sub": str(op_a.id), "role": op_a.role})
    res_a = unauthenticated_client.get(
        f"/api/v1/records/{record_id}/verification-report",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res_a.status_code == 200
    assert res_a.headers["content-type"] == "application/pdf"
    assert res_a.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_reviewer_and_viewer_universal_access_200(unauthenticated_client: TestClient, db_session: AsyncSession):
    """Verifies that Reviewers and Viewers have universal access to generate reports for any record."""
    admin, reviewer, viewer, op_a, op_b = create_test_users()
    db_session.add_all([admin, reviewer, viewer, op_a, op_b])

    record_id = uuid.uuid4()
    record = LandRecordModel(
        id=record_id,
        created_by=op_a.id,
        state="Rajasthan",
        district="Jaipur",
        tehsil="Sanganer",
        village="Rampura",
        khasra_number="404/D",
        khata_number="88",
        area_in_hectares=3.0000,
        land_classification="Commercial",
        owner_name="Heritage Hotels Ltd",
        confidence_score=0.96,
        status="VALIDATED",
        review_status="PENDING_REVIEW",
        created_at=datetime.utcnow()
    )
    db_session.add(record)
    await db_session.commit()

    # Reviewer access
    rev_token = create_access_token(data={"sub": str(reviewer.id), "role": reviewer.role})
    rev_res = unauthenticated_client.get(
        f"/api/v1/records/{record_id}/verification-report",
        headers={"Authorization": f"Bearer {rev_token}"}
    )
    assert rev_res.status_code == 200
    assert rev_res.content.startswith(b"%PDF-")

    # Viewer access
    view_token = create_access_token(data={"sub": str(viewer.id), "role": viewer.role})
    view_res = unauthenticated_client.get(
        f"/api/v1/records/{record_id}/verification-report",
        headers={"Authorization": f"Bearer {view_token}"}
    )
    assert view_res.status_code == 200
    assert view_res.content.startswith(b"%PDF-")


def test_missing_record_404(client: TestClient):
    """Verifies that requesting a non-existent record returns 404 Not Found."""
    non_existent_id = uuid.uuid4()
    res = client.get(f"/api/v1/records/{non_existent_id}/verification-report")
    assert res.status_code == 404
    assert "not found" in res.json()["message"].lower()


@pytest.mark.asyncio
async def test_record_with_no_discrepancies(client: TestClient, db_session: AsyncSession):
    """Verifies report generation when record has zero discrepancies."""
    record_id = uuid.uuid4()
    record = LandRecordModel(
        id=record_id,
        state="Rajasthan",
        district="Jaipur",
        tehsil="Sanganer",
        village="Rampura",
        khasra_number="505/E",
        khata_number="99",
        area_in_hectares=2.1000,
        land_classification="Agricultural",
        owner_name="Kailash Chand",
        confidence_score=0.98,
        status="VALIDATED",
        review_status="APPROVED",
        created_at=datetime.utcnow()
    )
    db_session.add(record)
    await db_session.commit()

    res = client.get(f"/api/v1/records/{record_id}/verification-report")
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_record_with_discrepancies_and_validation(client: TestClient, db_session: AsyncSession):
    """Verifies report generation including discrepancy details and validation results."""
    record_id = uuid.uuid4()
    record = LandRecordModel(
        id=record_id,
        state="Rajasthan",
        district="Jaipur",
        tehsil="Sanganer",
        village="Rampura",
        khasra_number="606/F",
        khata_number="112",
        area_in_hectares=5.4000,
        land_classification="Agricultural",
        owner_name="Sunil Verma",
        confidence_score=0.74,
        status="FLAGGED",
        review_status="PENDING_REVIEW",
        created_at=datetime.utcnow()
    )
    db_session.add(record)

    # Add discrepancy
    disc = DiscrepancyModel(
        id=uuid.uuid4(),
        record_id=record_id,
        discrepancy_type="AREA_MISMATCH",
        severity="HIGH",
        description="Declared area 5.4000 ha exceeds survey boundary area 4.8500 ha.",
        field_name="area_in_hectares",
        source_value="5.4000",
        conflicting_value="4.8500",
        confidence=0.85,
        status="OPEN",
        created_at=datetime.utcnow()
    )
    db_session.add(disc)

    # Add validation result
    val_res = ValidationResultModel(
        id=uuid.uuid4(),
        record_id=record_id,
        is_valid=False,
        status="FLAGGED",
        rule_results=[
            {"rule_name": "Area Boundary Check", "is_valid": False, "severity": "HIGH", "message": "Area outside allowable tolerance"},
            {"rule_name": "State Revenue Nomenclature", "is_valid": True, "severity": "INFO", "message": "Standard Rajasthan terms matched"}
        ],
        discrepancy_summary="Area discrepancy detected",
        validated_at=datetime.utcnow()
    )
    db_session.add(val_res)
    await db_session.commit()

    res = client.get(f"/api/v1/records/{record_id}/verification-report")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_record_with_low_confidence_fields(client: TestClient, db_session: AsyncSession):
    """Verifies that documents with low-confidence OCR fields generate reports highlighting low quality tiers."""
    doc_id = uuid.uuid4()
    doc = DocumentModel(
        id=doc_id,
        file_name="scanned_old_jamabandi.pdf",
        file_path="uploads/scanned_old_jamabandi.pdf",
        mime_type="application/pdf",
        file_size_bytes=45000,
        doc_type="JAMABANDI",
        status="VALIDATED",
        uploaded_at=datetime.utcnow()
    )
    db_session.add(doc)

    record_id = uuid.uuid4()
    record = LandRecordModel(
        id=record_id,
        document_id=doc_id,
        state="Rajasthan",
        district="Jaipur",
        tehsil="Sanganer",
        village="Rampura",
        khasra_number="707/G",
        khata_number="120",
        area_in_hectares=1.2000,
        land_classification="Agricultural",
        owner_name="Poor Quality OCR Owner",
        confidence_score=0.62,
        status="FLAGGED",
        review_status="PENDING_REVIEW",
        created_at=datetime.utcnow()
    )
    db_session.add(record)

    # Extraction result with low confidence fields
    ext = ExtractionResultModel(
        id=uuid.uuid4(),
        document_id=doc_id,
        provider="TESSERACT_OCR_V1",
        extracted_fields={
            "khasra_number": "707/G",
            "owner_name": "Poor Quality OCR Owner",
            "area_in_hectares": "1.2000"
        },
        field_confidences={
            "khasra_number": 0.58,
            "owner_name": 0.61,
            "area_in_hectares": 0.89
        },
        confidence_score=0.62,
        confidence_category="LOW",
        status="SUCCESS",
        extracted_at=datetime.utcnow()
    )
    db_session.add(ext)
    await db_session.commit()

    res = client.get(f"/api/v1/records/{record_id}/verification-report")
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_record_review_states_and_rejection_reason(client: TestClient, db_session: AsyncSession):
    """Verifies that different human review states (APPROVED, REJECTED with reason) are rendered cleanly."""
    reviewer_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    # 1. Approved record
    rec_approved_id = uuid.uuid4()
    rec_approved = LandRecordModel(
        id=rec_approved_id,
        state="Rajasthan",
        district="Jaipur",
        tehsil="Sanganer",
        village="Rampura",
        khasra_number="808/H",
        khata_number="133",
        area_in_hectares=2.4500,
        land_classification="Agricultural",
        owner_name="Deepak Joshi",
        confidence_score=0.94,
        status="VALIDATED",
        review_status="APPROVED",
        reviewed_by=reviewer_id,
        reviewed_at=datetime.utcnow(),
        review_notes="All field survey documents verified against master registry.",
        created_at=datetime.utcnow()
    )
    db_session.add(rec_approved)

    # 2. Rejected record
    rec_rejected_id = uuid.uuid4()
    rec_rejected = LandRecordModel(
        id=rec_rejected_id,
        state="Rajasthan",
        district="Jaipur",
        tehsil="Sanganer",
        village="Rampura",
        khasra_number="809/J",
        khata_number="134",
        area_in_hectares=3.0000,
        land_classification="Agricultural",
        owner_name="Invalid Claimant",
        confidence_score=0.71,
        status="REJECTED",
        review_status="REJECTED",
        reviewed_by=reviewer_id,
        reviewed_at=datetime.utcnow(),
        review_notes="Rejected after tehsildar inquiry.",
        rejection_reason="Duplicate registration number REG-9988 already claimed by another khatedar.",
        created_at=datetime.utcnow()
    )
    db_session.add(rec_rejected)
    await db_session.commit()

    res_app = client.get(f"/api/v1/records/{rec_approved_id}/verification-report")
    assert res_app.status_code == 200
    assert res_app.content.startswith(b"%PDF-")

    res_rej = client.get(f"/api/v1/records/{rec_rejected_id}/verification-report")
    assert res_rej.status_code == 200
    assert res_rej.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_safe_filename_sanitization(client: TestClient, db_session: AsyncSession):
    """Verifies that special characters in khasra numbers are strictly sanitized in the Content-Disposition filename."""
    record_id = uuid.uuid4()
    record = LandRecordModel(
        id=record_id,
        state="Rajasthan",
        district="Jaipur",
        tehsil="Sanganer",
        village="Rampura",
        khasra_number="104/2A #1 (Part-B)",
        khata_number="55",
        area_in_hectares=1.5000,
        land_classification="Agricultural",
        owner_name="Raju Lal",
        confidence_score=0.90,
        status="VALIDATED",
        review_status="PENDING_REVIEW",
        created_at=datetime.utcnow()
    )
    db_session.add(record)
    await db_session.commit()

    res = client.get(f"/api/v1/records/{record_id}/verification-report")
    assert res.status_code == 200
    disposition = res.headers["content-disposition"]
    # Check that /, #, (, ), and spaces are replaced with underscores, while hyphens are preserved
    assert "104_2A__1__Part-B_" in disposition
    assert disposition.endswith('.pdf"')


@pytest.mark.asyncio
async def test_malicious_field_sanitization(client: TestClient, db_session: AsyncSession):
    """Verifies that inputs containing HTML/script tags or unclosed markup are escaped without crashing ReportLab."""
    record_id = uuid.uuid4()
    record = LandRecordModel(
        id=record_id,
        state="Rajasthan",
        district="Jaipur",
        tehsil="Sanganer",
        village="<script>alert('XSS')</script>Village",
        khasra_number="999/X",
        khata_number="888",
        area_in_hectares=1.0000,
        land_classification="Agricultural",
        owner_name="<b>Unclosed Bold Tag & 'Quotes' <img src=x onerror=1>",
        confidence_score=0.85,
        status="VALIDATED",
        review_status="PENDING_REVIEW",
        review_notes="<iframe src='evil.com'></iframe> Notes",
        created_at=datetime.utcnow()
    )
    db_session.add(record)
    await db_session.commit()

    # Must generate cleanly without ReportLab XML parsing errors
    res = client.get(f"/api/v1/records/{record_id}/verification-report")
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_audit_event_logged_on_report_generation(client: TestClient, db_session: AsyncSession):
    """Verifies that generating a verification report logs a REPORT_GENERATED audit event in the database."""
    record_id = uuid.uuid4()
    record = LandRecordModel(
        id=record_id,
        state="Rajasthan",
        district="Jaipur",
        tehsil="Sanganer",
        village="Rampura",
        khasra_number="123/AUDIT",
        khata_number="789",
        area_in_hectares=2.3000,
        land_classification="Agricultural",
        owner_name="Audit Trail Owner",
        confidence_score=0.92,
        status="VALIDATED",
        review_status="APPROVED",
        created_at=datetime.utcnow()
    )
    db_session.add(record)
    await db_session.commit()

    res = client.get(f"/api/v1/records/{record_id}/verification-report")
    assert res.status_code == 200

    # Query audit logs
    async with TestAsyncSessionLocal() as session:
        stmt = (
            select(AuditLogModel)
            .where(
                AuditLogModel.entity_type == "LAND_RECORD",
                AuditLogModel.entity_id == record_id,
                AuditLogModel.action == "REPORT_GENERATED"
            )
        )
        audit_res = await session.execute(stmt)
        event = audit_res.scalars().first()
        assert event is not None
        assert event.new_state is not None
        assert "VR-" in event.new_state["report_reference"]
        assert event.new_state["khasra_number"] == "123/AUDIT"
        assert event.new_state["file_size_bytes"] > 0
