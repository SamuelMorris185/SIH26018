import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.land_record import LandRecordModel
from app.services.comparison_service import comparison_service
from app.schemas.discrepancy import DiscrepancyType, DiscrepancySeverity, DiscrepancyStatus, DiscrepancyUpdate

def create_mock_record(
    khasra="104/2",
    khata="45",
    village="Bairagarh",
    tehsil="Huzur",
    district="Bhopal",
    state="Madhya Pradesh",
    area=1.2500,
    owner="Ram Prasad Sharma",
    co_owners=None,
    classification="Agricultural",
    conf=0.95
) -> LandRecordModel:
    return LandRecordModel(
        id=uuid.uuid4(),
        state=state,
        district=district,
        tehsil=tehsil,
        village=village,
        khasra_number=khasra,
        khata_number=khata,
        area_in_hectares=area,
        land_classification=classification,
        owner_name=owner,
        co_owners=co_owners or ["Shyam Prasad Sharma"],
        confidence_score=conf,
        status="VALIDATED"
    )

def test_owner_mismatch_rule():
    rec1 = create_mock_record(owner="Ram Prasad Sharma")
    rec2 = create_mock_record(owner="Vikram Aditya Singh")

    discrepancies = comparison_service.evaluate_pair(rec2, rec1)
    types = [d["discrepancy_type"] for d in discrepancies]
    assert DiscrepancyType.OWNER_MISMATCH.value in types

    disc = next(d for d in discrepancies if d["discrepancy_type"] == DiscrepancyType.OWNER_MISMATCH.value)
    assert disc["severity"] in {DiscrepancySeverity.CRITICAL.value, DiscrepancySeverity.HIGH.value}
    assert disc["source_value"] == "Vikram Aditya Singh"
    assert disc["conflicting_value"] == "Ram Prasad Sharma"

def test_co_owner_mismatch_rule():
    rec1 = create_mock_record(co_owners=["Shyam Prasad Sharma"])
    rec2 = create_mock_record(co_owners=["Rajesh Kumar"])

    discrepancies = comparison_service.evaluate_pair(rec2, rec1)
    types = [d["discrepancy_type"] for d in discrepancies]
    assert DiscrepancyType.CO_OWNER_MISMATCH.value in types

def test_area_mismatch_rule():
    rec1 = create_mock_record(area=1.2500)
    # 1. Divergence within tolerance (0.005 ha <= 0.01 ha) -> No discrepancy
    rec2_fine = create_mock_record(area=1.2505)
    discrepancies_fine = comparison_service.evaluate_pair(rec2_fine, rec1)
    assert DiscrepancyType.AREA_MISMATCH.value not in [d["discrepancy_type"] for d in discrepancies_fine]

    # 2. Divergence exceeding tolerance (3.75 ha vs 1.25 ha) -> Discrepancy
    rec3_conflict = create_mock_record(area=3.7500)
    discrepancies_conflict = comparison_service.evaluate_pair(rec3_conflict, rec1)
    types = [d["discrepancy_type"] for d in discrepancies_conflict]
    assert DiscrepancyType.AREA_MISMATCH.value in types

def test_survey_conflict_rule():
    rec1 = create_mock_record(classification="Agricultural")
    rec2 = create_mock_record(classification="Commercial")

    discrepancies = comparison_service.evaluate_pair(rec2, rec1)
    types = [d["discrepancy_type"] for d in discrepancies]
    assert DiscrepancyType.SURVEY_CONFLICT.value in types

def test_duplicate_document_rule():
    doc1 = uuid.uuid4()
    doc2 = uuid.uuid4()
    rec1 = create_mock_record()
    rec1.document_id = doc1
    rec2 = create_mock_record()
    rec2.document_id = doc2

    discrepancies = comparison_service.evaluate_pair(rec2, rec1)
    types = [d["discrepancy_type"] for d in discrepancies]
    assert DiscrepancyType.DUPLICATE_DOCUMENT.value in types

def test_self_record_low_confidence():
    rec_low = create_mock_record(conf=0.45)
    discrepancies = comparison_service.evaluate_self_record(rec_low)
    types = [d["discrepancy_type"] for d in discrepancies]
    assert DiscrepancyType.LOW_CONFIDENCE_CRITICAL_FIELD.value in types

    rec_good = create_mock_record(conf=0.92)
    discrepancies_good = comparison_service.evaluate_self_record(rec_good)
    assert len(discrepancies_good) == 0

@pytest.mark.asyncio
async def test_idempotent_comparison_execution(db_session: AsyncSession):
    # Setup 2 conflicting records in session
    rec_baseline = create_mock_record(owner="Ram Prasad Sharma", area=1.2500)
    db_session.add(rec_baseline)
    await db_session.flush()

    rec_new = create_mock_record(owner="Vikram Aditya Singh", area=3.7500)
    db_session.add(rec_new)
    await db_session.flush()

    # Run comparison 1st time
    summary1 = await comparison_service.compare_record(db_session, rec_new.id)
    assert summary1.total_discrepancies >= 2
    assert rec_new.status == "FLAGGED"

    # Run comparison 2nd time on identical record -> Idempotent, must not duplicate discrepancies
    summary2 = await comparison_service.compare_record(db_session, rec_new.id)
    assert summary2.total_discrepancies == summary1.total_discrepancies

    discs = await comparison_service.get_record_discrepancies(db_session, rec_new.id)
    assert len(discs) == summary1.total_discrepancies
