import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.search_service import SearchService
from app.services.land_record_service import LandRecordService
from app.schemas.record import LandRecordCreate

@pytest.mark.anyio
async def test_search_service(db_session: AsyncSession):
    record_service = LandRecordService()
    search = SearchService()

    # Seed 3 records
    r1 = await record_service.create_record(
        db_session,
        LandRecordCreate(
            state="Madhya Pradesh",
            district="Bhopal",
            tehsil="Huzur",
            village="Bairagarh",
            khasra_number="101",
            khata_number="10",
            area_in_hectares=1.0,
            status="VALIDATED"
        )
    )
    r2 = await record_service.create_record(
        db_session,
        LandRecordCreate(
            state="Madhya Pradesh",
            district="Bhopal",
            tehsil="Huzur",
            village="Bairagarh",
            khasra_number="102/1",
            khata_number="12",
            area_in_hectares=2.5,
            status="FLAGGED"
        )
    )
    r3 = await record_service.create_record(
        db_session,
        LandRecordCreate(
            state="Uttar Pradesh",
            district="Varanasi",
            tehsil="Sadar",
            village="Shivpur",
            khasra_number="505",
            khata_number="88",
            area_in_hectares=0.75,
            status="VALIDATED"
        )
    )

    # 1. Search by state (case-insensitive)
    res_mp = await search.search_records(db_session, state="madhya pradesh")
    assert res_mp.total == 2
    assert len(res_mp.data) == 2

    # 2. Search by status
    res_flagged = await search.search_records(db_session, status="FLAGGED")
    assert res_flagged.total == 1
    assert res_flagged.data[0].khasra_number == "102/1"

    # 3. Partial khasra match
    res_khasra = await search.search_records(db_session, khasra_number="102")
    assert res_khasra.total == 1

    # 4. Area range filtering
    res_area = await search.search_records(db_session, min_area=2.0)
    assert res_area.total == 1
    assert res_area.data[0].khasra_number == "102/1"

    # 5. Empty search results
    res_empty = await search.search_records(db_session, state="Goa")
    assert res_empty.total == 0
    assert len(res_empty.data) == 0

    # 6. Pagination
    res_page = await search.search_records(db_session, limit=2, page=1)
    assert res_page.total == 3
    assert len(res_page.data) == 2
    assert res_page.total_pages == 2
