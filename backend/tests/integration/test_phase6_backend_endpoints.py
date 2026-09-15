import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, create_access_token
from app.models.user import UserModel
from app.models.document import DocumentModel
from app.models.land_record import LandRecordModel
from app.models.discrepancy import DiscrepancyModel
from app.services.storage_service import storage_service

@pytest.mark.anyio
async def test_phase6_endpoints(unauthenticated_client: TestClient, db_session: AsyncSession):
    # 1. Setup authenticated user
    user = UserModel(
        id=uuid.UUID("77777777-8888-9999-aaaa-bbbbbbbbbbbb"),
        email="phase6_test@revenue.gov.in",
        hashed_password=get_password_hash("Phase6Pass123!"),
        full_name="Phase 6 Tester",
        role="ADMIN",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)

    # 2. Save physical file in storage and register document
    test_content = b"PDF Mock Content for Phase 6 Testing"
    storage_path, file_size = await storage_service.save_file(
        test_content, "test_doc_p6.pdf", "application/pdf"
    )

    doc = DocumentModel(
        id=uuid.uuid4(),
        file_name="test_doc_p6.pdf",
        file_path=storage_path,
        mime_type="application/pdf",
        file_size_bytes=file_size,
        doc_type="JAMABANDI",
        status="VALIDATED",
        created_by=user.id,
        uploaded_at=datetime.utcnow()
    )
    db_session.add(doc)

    record = LandRecordModel(
        id=uuid.uuid4(),
        document_id=doc.id,
        created_by=user.id,
        state="Madhya Pradesh",
        district="Bhopal",
        tehsil="Huzur",
        village="Bairagarh",
        khasra_number="104/2",
        khata_number="45",
        area_in_hectares=1.25,
        land_classification="Agricultural",
        owner_name="Test Owner",
        status="VALIDATED",
        review_status="APPROVED",
        confidence_score=0.95,
        created_at=datetime.utcnow()
    )
    db_session.add(record)

    disc = DiscrepancyModel(
        id=uuid.uuid4(),
        record_id=record.id,
        discrepancy_type="OWNER_MISMATCH",
        severity="HIGH",
        description="Phase 6 test discrepancy",
        field_name="owner_name",
        source_value="Test Owner",
        conflicting_value="Old Owner",
        confidence=0.85,
        status="OPEN",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(disc)
    await db_session.commit()

    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    # Test GET /api/v1/system/dashboard-stats
    assert unauthenticated_client.get("/api/v1/system/dashboard-stats").status_code == 401
    stats_resp = unauthenticated_client.get("/api/v1/system/dashboard-stats", headers=headers)
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()
    assert "total_records" in stats_data
    assert "documents_processed" in stats_data
    assert "records_awaiting_review" in stats_data
    assert "validated_records" in stats_data
    assert "flagged_records" in stats_data
    assert "open_discrepancies" in stats_data
    assert stats_data["total_records"] >= 1
    assert stats_data["validated_records"] >= 1
    assert stats_data["open_discrepancies"] >= 1

    # Test GET /api/v1/discrepancies
    disc_resp = unauthenticated_client.get("/api/v1/discrepancies", headers=headers)
    assert disc_resp.status_code == 200
    disc_data = disc_resp.json()
    assert "total" in disc_data
    assert "data" in disc_data
    assert disc_data["total"] >= 1
    assert any(d["id"] == str(disc.id) for d in disc_data["data"])

    # Test filtered GET /api/v1/discrepancies
    filt_resp = unauthenticated_client.get("/api/v1/discrepancies?status=OPEN&severity=HIGH", headers=headers)
    assert filt_resp.status_code == 200
    assert filt_resp.json()["total"] >= 1

    # Test GET /api/v1/documents/{document_id}/content
    content_resp = unauthenticated_client.get(f"/api/v1/documents/{doc.id}/content", headers=headers)
    assert content_resp.status_code == 200
    assert content_resp.content == test_content
    assert content_resp.headers["content-type"] == "application/pdf"
    assert 'filename="test_doc_p6.pdf"' in content_resp.headers["content-disposition"]
