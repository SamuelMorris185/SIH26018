import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.land_record_service import LandRecordService
from app.schemas.record import LandRecordCreate, LandRecordUpdate
from app.core.exceptions import RecordNotFoundError, InvalidStateTransitionError

@pytest.mark.anyio
async def test_land_record_lifecycle(db_session: AsyncSession):
    service = LandRecordService()
    doc_id = uuid.uuid4()

    # 1. Create Record
    payload = LandRecordCreate(
        document_id=doc_id,
        state="Madhya Pradesh",
        district="Bhopal",
        tehsil="Huzur",
        village="Bairagarh",
        khasra_number="104/2",
        khata_number="45",
        area_in_hectares=1.25,
        land_classification="Agricultural",
        confidence_score=0.95,
        status="EXTRACTED"
    )
    record = await service.create_record(db_session, payload)
    assert record.id is not None
    assert record.status == "EXTRACTED"
    assert record.document_id == doc_id

    # 2. Get Record
    fetched = await service.get_record(db_session, record.id)
    assert fetched.khasra_number == "104/2"

    # 3. Update Record Fields & Status
    update_payload = LandRecordUpdate(
        area_in_hectares=1.50,
        status="VALIDATED"
    )
    updated = await service.update_record(db_session, record.id, update_payload)
    assert float(updated.area_in_hectares) == 1.50
    assert updated.status == "VALIDATED"

    # 4. Invalid State Transition: VALIDATED cannot transition back to EXTRACTED
    with pytest.raises(InvalidStateTransitionError):
        await service.update_record(db_session, record.id, LandRecordUpdate(status="EXTRACTED"))

    # 5. List by Document
    records_for_doc = await service.list_by_document(db_session, doc_id)
    assert len(records_for_doc) == 1
    assert records_for_doc[0].id == record.id

    # 5. Not Found
    with pytest.raises(RecordNotFoundError):
        await service.get_record(db_session, uuid.uuid4())
