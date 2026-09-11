import uuid
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, asc, desc

from app.core.logging import logger
from app.models.land_record import LandRecordModel
from app.schemas.record import LandRecordResponse, LandRecordPaginatedList

class SearchService:
    """
    High-performance, database-level query and search service for Land Records.
    Executes filtered, paginated, and ordered queries directly in SQL.
    """

    SORTABLE_FIELDS = {
        "created_at": LandRecordModel.created_at,
        "updated_at": LandRecordModel.updated_at,
        "area_in_hectares": LandRecordModel.area_in_hectares,
        "khasra_number": LandRecordModel.khasra_number,
        "village": LandRecordModel.village,
        "status": LandRecordModel.status,
    }

    async def search_records(
        self,
        session: AsyncSession,
        state: Optional[str] = None,
        district: Optional[str] = None,
        tehsil: Optional[str] = None,
        village: Optional[str] = None,
        khasra_number: Optional[str] = None,
        khata_number: Optional[str] = None,
        status: Optional[str] = None,
        document_id: Optional[uuid.UUID] = None,
        min_area: Optional[float] = None,
        max_area: Optional[float] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        limit: int = 20
    ) -> LandRecordPaginatedList:
        """
        Executes multi-criteria filtered search with SQL-level pagination and ordering.
        """
        # Build base filter conditions
        conditions = []

        if state:
            conditions.append(func.lower(LandRecordModel.state) == state.strip().lower())
        if district:
            conditions.append(func.lower(LandRecordModel.district) == district.strip().lower())
        if tehsil:
            conditions.append(func.lower(LandRecordModel.tehsil) == tehsil.strip().lower())
        if village:
            conditions.append(func.lower(LandRecordModel.village) == village.strip().lower())
        if khasra_number:
            conditions.append(LandRecordModel.khasra_number.ilike(f"%{khasra_number.strip()}%"))
        if khata_number:
            conditions.append(LandRecordModel.khata_number == khata_number.strip())
        if status:
            conditions.append(func.lower(LandRecordModel.status) == status.strip().lower())
        if document_id:
            conditions.append(LandRecordModel.document_id == document_id)
        if min_area is not None:
            conditions.append(LandRecordModel.area_in_hectares >= min_area)
        if max_area is not None:
            conditions.append(LandRecordModel.area_in_hectares <= max_area)

        # Count total matching records in SQL
        count_stmt = select(func.count(LandRecordModel.id))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        
        count_res = await session.execute(count_stmt)
        total = count_res.scalar_one()

        # Build paginated query
        query = select(LandRecordModel)
        if conditions:
            query = query.where(*conditions)

        # Sorting
        sort_col = self.SORTABLE_FIELDS.get(sort_by, LandRecordModel.created_at)
        order_func = desc if sort_order.lower() == "desc" else asc
        query = query.order_by(order_func(sort_col))

        # Pagination offsets
        safe_limit = max(1, min(limit, 100))
        safe_page = max(1, page)
        offset = (safe_page - 1) * safe_limit

        query = query.offset(offset).limit(safe_limit)
        records_res = await session.execute(query)
        records = list(records_res.scalars().all())

        total_pages = (total + safe_limit - 1) // safe_limit if total > 0 else 0

        logger.debug(f"Search executed: found {total} records, returning page {safe_page}/{total_pages}")

        return LandRecordPaginatedList(
            total=total,
            page=safe_page,
            limit=safe_limit,
            total_pages=total_pages,
            data=[LandRecordResponse.model_validate(r) for r in records]
        )

# Global default instance
search_service = SearchService()
