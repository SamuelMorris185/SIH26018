import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, create_access_token
from app.models.user import UserModel
from app.models.document import DocumentModel
from app.models.land_record import LandRecordModel
from app.models.extraction import ExtractionResultModel
from app.models.discrepancy import DiscrepancyModel, RecordComparisonModel

def create_users():
    admin = UserModel(
        id=uuid.UUID("11111111-2222-3333-4444-111111111111"),
        email="admin_disc@sih.gov.in",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Admin User",
        role="ADMIN",
        is_active=True,
        created_at=datetime.utcnow()
    )
    operator1 = UserModel(
        id=uuid.UUID("22222222-3333-4444-5555-111111111111"),
        email="operator1_disc@sih.gov.in",
        hashed_password=get_password_hash("OpPass123!"),
        full_name="Operator One",
        role="OPERATOR",
        is_active=True,
        created_at=datetime.utcnow()
    )
    operator2 = UserModel(
        id=uuid.UUID("33333333-4444-5555-6666-111111111111"),
        email="operator2_disc@sih.gov.in",
        hashed_password=get_password_hash("OpPass123!"),
        full_name="Operator Two",
        role="OPERATOR",
        is_active=True,
        created_at=datetime.utcnow()
    )
    reviewer = UserModel(
        id=uuid.UUID("44444444-5555-6666-7777-111111111111"),
        email="reviewer_disc@sih.gov.in",
        hashed_password=get_password_hash("RevPass123!"),
        full_name="Reviewer User",
        role="REVIEWER",
        is_active=True,
        created_at=datetime.utcnow()
    )
    return admin, operator1, operator2, reviewer

@pytest.mark.anyio
async def test_discrepancy_api_endpoints_and_rbac(unauthenticated_client: TestClient, db_session: AsyncSession):
    admin, operator1, operator2, reviewer = create_users()
    db_session.add_all([admin, operator1, operator2, reviewer])

    # 1. Create a document and land record owned by Operator 1
    doc = DocumentModel(
        id=uuid.uuid4(),
        file_name="record_104_2.pdf",
        file_path="uploads/record_104_2.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        doc_type="JAMABANDI",
        status="EXTRACTED",
        created_by=operator1.id,
        uploaded_at=datetime.utcnow()
    )
    db_session.add(doc)

    ext = ExtractionResultModel(
        id=uuid.uuid4(),
        document_id=doc.id,
        provider="MOCK_OCR_V1",
        raw_text="Extracted text...",
        extracted_fields={"khasra_number": "104/2", "owner_name": "Ram Prasad Sharma"},
        structured_fields={
            "owner_name": {
                "field": "owner_name",
                "value": "Ram Prasad Sharma",
                "confidence": 0.95,
                "category": "HIGH",
                "source": "mock"
            }
        },
        confidence_score=0.95,
        confidence_category="HIGH",
        status="SUCCESS",
        extracted_at=datetime.utcnow()
    )
    db_session.add(ext)

    rec = LandRecordModel(
        id=uuid.uuid4(),
        document_id=doc.id,
        created_by=operator1.id,
        state="Madhya Pradesh",
        district="Bhopal",
        tehsil="Huzur",
        village="Bairagarh",
        khasra_number="104/2",
        khata_number="45",
        area_in_hectares=1.2500,
        land_classification="Agricultural",
        owner_name="Ram Prasad Sharma",
        confidence_score=0.95,
        status="FLAGGED",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(rec)

    disc = DiscrepancyModel(
        id=uuid.uuid4(),
        record_id=rec.id,
        discrepancy_type="OWNER_MISMATCH",
        severity="HIGH",
        description="Conflicting owner name detected.",
        source_value="Ram Prasad Sharma",
        conflicting_value="Vikram Aditya Singh",
        confidence=0.95,
        status="OPEN",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(disc)
    await db_session.commit()

    # Tokens
    op1_token = create_access_token({"sub": str(operator1.id), "role": operator1.role})
    op2_token = create_access_token({"sub": str(operator2.id), "role": operator2.role})
    rev_token = create_access_token({"sub": str(reviewer.id), "role": reviewer.role})

    # Test A: Unauthenticated request fails (401)
    res_anon = unauthenticated_client.get(f"/api/v1/records/{rec.id}/discrepancies")
    assert res_anon.status_code == 401

    # Test B: Operator 2 cannot access Operator 1's record discrepancies (403 Forbidden)
    res_op2 = unauthenticated_client.get(
        f"/api/v1/records/{rec.id}/discrepancies",
        headers={"Authorization": f"Bearer {op2_token}"}
    )
    assert res_op2.status_code == 403

    # Test C: Operator 1 (owner) can access discrepancies (200 OK)
    res_op1 = unauthenticated_client.get(
        f"/api/v1/records/{rec.id}/discrepancies",
        headers={"Authorization": f"Bearer {op1_token}"}
    )
    assert res_op1.status_code == 200
    disc_list = res_op1.json()
    assert len(disc_list) == 1
    assert disc_list[0]["discrepancy_type"] == "OWNER_MISMATCH"

    # Test D: Get Record Extraction Endpoint
    res_ext = unauthenticated_client.get(
        f"/api/v1/records/{rec.id}/extraction",
        headers={"Authorization": f"Bearer {op1_token}"}
    )
    assert res_ext.status_code == 200
    ext_data = res_ext.json()
    assert ext_data["provider"] == "MOCK_OCR_V1"
    assert "owner_name" in ext_data["structured_fields"]

    # Test E: Operator cannot update discrepancy status (403 Forbidden)
    res_update_op = unauthenticated_client.patch(
        f"/api/v1/discrepancies/{disc.id}",
        json={"status": "RESOLVED", "resolution_notes": "Attempted operator resolution"},
        headers={"Authorization": f"Bearer {op1_token}"}
    )
    assert res_update_op.status_code == 403

    # Test F: Reviewer can update discrepancy status (200 OK)
    res_update_rev = unauthenticated_client.patch(
        f"/api/v1/discrepancies/{disc.id}",
        json={"status": "RESOLVED", "resolution_notes": "Verified by Revenue Inspector order #44"},
        headers={"Authorization": f"Bearer {rev_token}"}
    )
    assert res_update_rev.status_code == 200
    updated_disc = res_update_rev.json()
    assert updated_disc["status"] == "RESOLVED"
