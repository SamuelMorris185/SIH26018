import uuid
import math
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.core.exceptions import (
    RecordNotFoundError,
    ForbiddenError,
    DomainException,
)
from app.models.land_record import LandRecordModel
from app.models.parcel_location import ParcelLocationModel
from app.models.user import UserModel
from app.schemas.user import UserRole
from app.schemas.gis import (
    ParcelLocationBase,
    CadastralMapRecord,
    GeometryValidationResponse,
)
from app.services.audit_service import audit_service

class GisService:
    """
    GIS and Cadastral Parcel Location Service.
    Enforces coordinate validation, GeoJSON geometry integrity, data minimization, and RBAC isolation.
    """

    @staticmethod
    def validate_coordinates(lat: Optional[float], lon: Optional[float]) -> Tuple[bool, List[str]]:
        """
        Validates latitude (-90 to 90) and longitude (-180 to 180).
        Rejects non-numeric, NaN, and Infinite values.
        """
        errors = []
        if lat is not None:
            if not isinstance(lat, (int, float)) or math.isnan(lat) or math.isinf(lat):
                errors.append("Latitude must be a valid finite number.")
            elif not (-90.0 <= lat <= 90.0):
                errors.append(f"Latitude {lat} is out of bounds (must be between -90.0 and 90.0).")

        if lon is not None:
            if not isinstance(lon, (int, float)) or math.isnan(lon) or math.isinf(lon):
                errors.append("Longitude must be a valid finite number.")
            elif not (-180.0 <= lon <= 180.0):
                errors.append(f"Longitude {lon} is out of bounds (must be between -180.0 and 180.0).")

        return (len(errors) == 0), errors

    @staticmethod
    def validate_geojson(geojson_dict: Optional[Dict[str, Any]]) -> Tuple[bool, Optional[str], int, List[str]]:
        """
        Validates structure, geometry types, vertex count, and coordinate topology.
        Supported types: Polygon, MultiPolygon, Point, Feature.
        """
        if not geojson_dict:
            return True, None, 0, []

        errors = []
        if not isinstance(geojson_dict, dict):
            return False, None, 0, ["GeoJSON payload must be a JSON object."]

        # Check for untrusted script injection
        raw_str = str(geojson_dict).lower()
        if "<script" in raw_str or "javascript:" in raw_str or "onerror" in raw_str:
            return False, None, 0, ["GeoJSON payload contains prohibited script tags or executable content."]

        geom_obj = geojson_dict
        if geojson_dict.get("type") == "Feature":
            geom_obj = geojson_dict.get("geometry")
            if not geom_obj or not isinstance(geom_obj, dict):
                return False, "Feature", 0, ["GeoJSON Feature must contain a valid 'geometry' object."]

        geom_type = geom_obj.get("type")
        allowed_types = ["Polygon", "MultiPolygon", "Point"]
        if geom_type not in allowed_types:
            return False, geom_type, 0, [
                f"Unsupported geometry type '{geom_type}'. Supported types: {', '.join(allowed_types)}."
            ]

        coords = geom_obj.get("coordinates")
        if coords is None or not isinstance(coords, list):
            return False, geom_type, 0, ["Geometry must contain a 'coordinates' list."]
        if not coords:
            return False, geom_type, 0, ["Geometry coordinates must not be empty."]

        vertex_count = 0
        MAX_VERTICES = 5000

        def validate_ring(ring: Any) -> bool:
            nonlocal vertex_count
            if not isinstance(ring, list) or len(ring) < 4:
                errors.append("Polygon linear ring must contain at least 4 coordinate pairs.")
                return False
            # Closed ring check
            first_pt = ring[0]
            last_pt = ring[-1]
            if first_pt != last_pt:
                errors.append("Polygon linear ring must be closed (first and last vertex must match).")
                return False
            for pt in ring:
                vertex_count += 1
                if vertex_count > MAX_VERTICES:
                    errors.append(f"Geometry exceeds maximum vertex limit ({MAX_VERTICES}).")
                    return False
                if not isinstance(pt, list) or len(pt) < 2:
                    errors.append(f"Invalid coordinate format: {pt}. Expected [longitude, latitude].")
                    return False
                lon, lat = pt[0], pt[1]
                if not isinstance(lon, (int, float)) or not (-180.0 <= lon <= 180.0):
                    errors.append(f"Longitude {lon} out of range (-180 to 180).")
                if not isinstance(lat, (int, float)) or not (-90.0 <= lat <= 90.0):
                    errors.append(f"Latitude {lat} out of range (-90 to 90).")
            return len(errors) == 0

        if geom_type == "Point":
            vertex_count = 1
            if len(coords) < 2 or not isinstance(coords[0], (int, float)) or not isinstance(coords[1], (int, float)):
                errors.append("Point coordinates must be [longitude, latitude].")
            else:
                _, point_errors = GisService.validate_coordinates(coords[1], coords[0])
                errors.extend(point_errors)

        elif geom_type == "Polygon":
            for ring in coords:
                if not validate_ring(ring):
                    break

        elif geom_type == "MultiPolygon":
            for poly in coords:
                if not isinstance(poly, list) or not poly:
                    errors.append("MultiPolygon coordinates must be a list of Polygons.")
                    break
                for ring in poly:
                    if not validate_ring(ring):
                        break

        is_valid = len(errors) == 0
        return is_valid, geom_type, vertex_count, errors

    def validate_geometry_payload(
        self,
        lat: Optional[float],
        lon: Optional[float],
        geojson: Optional[Dict[str, Any]],
        coordinate_reference_system: str = "EPSG:4326",
    ) -> GeometryValidationResponse:
        """
        Comprehensive validation of coordinates and GeoJSON boundary.
        """
        all_errors = []
        all_warnings = []
        if coordinate_reference_system != "EPSG:4326":
            all_errors.append("Only EPSG:4326 coordinates are supported.")
        if (lat is None) != (lon is None):
            all_errors.append("Latitude and longitude must be provided together.")

        coords_valid, coord_errs = self.validate_coordinates(lat, lon)
        all_errors.extend(coord_errs)

        geo_valid, geom_type, v_count, geo_errs = self.validate_geojson(geojson)
        all_errors.extend(geo_errs)

        if lat is None and lon is None and geojson is None:
            all_warnings.append("No spatial coordinates or boundary provided.")

        return GeometryValidationResponse(
            is_valid=(len(all_errors) == 0),
            geometry_type=geom_type,
            vertex_count=v_count,
            coordinate_reference_system="EPSG:4326",
            errors=all_errors,
            warnings=all_warnings
        )

    async def attach_parcel_location(
        self,
        session: AsyncSession,
        record_id: uuid.UUID,
        location_data: ParcelLocationBase,
        current_user: UserModel
    ) -> ParcelLocationModel:
        """
        Attaches or updates spatial parcel coordinates and GeoJSON boundary for a land record.
        Enforces validation and RBAC ownership.
        """
        # 1. Fetch land record
        record_res = await session.execute(
            select(LandRecordModel).where(LandRecordModel.id == record_id)
        )
        record = record_res.scalar_one_or_none()
        if not record:
            raise RecordNotFoundError(record_id)

        # RBAC Check: ADMIN or owner
        is_admin = current_user.role == UserRole.ADMIN or str(current_user.role) == "ADMIN"
        if not is_admin and record.created_by != current_user.id:
            raise ForbiddenError("You do not have permission to attach spatial geometry to this land record.")

        # 2. Validate geometry
        val_result = self.validate_geometry_payload(
            lat=location_data.latitude,
            lon=location_data.longitude,
            geojson=location_data.boundary_geojson,
            coordinate_reference_system=location_data.coordinate_reference_system,
        )
        if not val_result.is_valid:
            raise DomainException(
                message=f"Invalid spatial geometry: {'; '.join(val_result.errors)}",
                status_code=422,
                details={"errors": val_result.errors}
            )

        # 3. Check existing parcel location
        loc_res = await session.execute(
            select(ParcelLocationModel).where(ParcelLocationModel.record_id == record_id)
        )
        parcel_loc = loc_res.scalar_one_or_none()

        action = "PARCEL_LOCATION_UPDATED" if parcel_loc else "PARCEL_LOCATION_CREATED"
        if parcel_loc:
            parcel_loc.latitude = location_data.latitude
            parcel_loc.longitude = location_data.longitude
            parcel_loc.boundary_geojson = location_data.boundary_geojson
            parcel_loc.coordinate_reference_system = location_data.coordinate_reference_system
            parcel_loc.geometry_validation_status = "VALID"
            parcel_loc.map_source = location_data.map_source
            parcel_loc.location_confidence = location_data.location_confidence
            parcel_loc.updated_at = datetime.utcnow()
        else:
            parcel_loc = ParcelLocationModel(
                id=uuid.uuid4(),
                record_id=record_id,
                latitude=location_data.latitude,
                longitude=location_data.longitude,
                boundary_geojson=location_data.boundary_geojson,
                coordinate_reference_system=location_data.coordinate_reference_system,
                geometry_validation_status="VALID",
                map_source=location_data.map_source,
                location_confidence=location_data.location_confidence,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(parcel_loc)

        await session.flush()

        await audit_service.log_event(
            session=session,
            action=action,
            entity_type="PARCEL_LOCATION",
            actor_user_id=current_user.id,
            entity_id=parcel_loc.id,
            new_state={
                "record_id": str(record_id),
                "latitude": parcel_loc.latitude,
                "longitude": parcel_loc.longitude,
                "source": parcel_loc.map_source
            }
        )
        logger.info(f"Spatial location attached to record {record_id} by {current_user.id}")
        return parcel_loc

    async def list_cadastral_parcels(
        self,
        session: AsyncSession,
        current_user: UserModel,
        status_filter: Optional[str] = None,
        district_filter: Optional[str] = None,
        village_filter: Optional[str] = None,
        has_discrepancies: Optional[bool] = None,
        limit: int = 300
    ) -> List[CadastralMapRecord]:
        """
        Queries land records with associated spatial locations, applying RBAC and data minimization.
        Only returns non-sensitive features required for map visualization.
        """
        query = (
            select(LandRecordModel, ParcelLocationModel)
            .join(ParcelLocationModel, LandRecordModel.id == ParcelLocationModel.record_id)
            .options(selectinload(LandRecordModel.discrepancies))
        )

        filters = []
        is_admin = current_user.role == UserRole.ADMIN or str(current_user.role) == "ADMIN"
        if not is_admin:
            filters.append(LandRecordModel.created_by == current_user.id)

        if status_filter:
            filters.append(LandRecordModel.status == status_filter.upper())
        if district_filter:
            filters.append(LandRecordModel.district.ilike(f"%{district_filter}%"))
        if village_filter:
            filters.append(LandRecordModel.village.ilike(f"%{village_filter}%"))
        if has_discrepancies is not None:
            filters.append(LandRecordModel.discrepancies.any() == has_discrepancies)

        # Only return records that have a valid coordinate or boundary
        filters.append(
            or_(
                ParcelLocationModel.latitude.isnot(None),
                ParcelLocationModel.boundary_geojson.isnot(None)
            )
        )

        query = query.where(*filters).order_by(desc(LandRecordModel.created_at)).limit(limit)
        results = await session.execute(query)

        map_records: List[CadastralMapRecord] = []
        for record, location in results.all():
            disc_count = len(record.discrepancies) if record.discrepancies else 0
            has_disc = disc_count > 0

            if has_discrepancies is not None and has_disc != has_discrepancies:
                continue

            map_records.append(
                CadastralMapRecord(
                    record_id=record.id,
                    khasra_number=record.khasra_number,
                    khata_number=record.khata_number,
                    state=record.state,
                    district=record.district,
                    tehsil=record.tehsil,
                    village=record.village,
                    area_in_hectares=float(record.area_in_hectares),
                    land_classification=record.land_classification,
                    status=record.status,
                    review_status=record.review_status,
                    confidence_score=record.confidence_score,
                    has_discrepancies=has_disc,
                    discrepancy_count=disc_count,
                    latitude=location.latitude,
                    longitude=location.longitude,
                    boundary_geojson=location.boundary_geojson,
                    geometry_validation_status=location.geometry_validation_status,
                    map_source=location.map_source
                )
            )

        return map_records

    async def get_parcel_detail(
        self,
        session: AsyncSession,
        record_id: uuid.UUID,
        current_user: UserModel
    ) -> CadastralMapRecord:
        """
        Retrieves map parcel detail for a specific record with RBAC verification.
        """
        query = (
            select(LandRecordModel, ParcelLocationModel)
            .outerjoin(ParcelLocationModel, LandRecordModel.id == ParcelLocationModel.record_id)
            .options(selectinload(LandRecordModel.discrepancies))
            .where(LandRecordModel.id == record_id)
        )
        res = await session.execute(query)
        row = res.first()
        if not row:
            raise RecordNotFoundError(record_id)

        record, location = row
        is_admin = current_user.role == UserRole.ADMIN or str(current_user.role) == "ADMIN"
        if not is_admin and record.created_by != current_user.id:
            raise ForbiddenError("You do not have permission to view spatial data for this land record.")

        disc_count = len(record.discrepancies) if record.discrepancies else 0

        return CadastralMapRecord(
            record_id=record.id,
            khasra_number=record.khasra_number,
            khata_number=record.khata_number,
            state=record.state,
            district=record.district,
            tehsil=record.tehsil,
            village=record.village,
            area_in_hectares=float(record.area_in_hectares),
            land_classification=record.land_classification,
            status=record.status,
            review_status=record.review_status,
            confidence_score=record.confidence_score,
            has_discrepancies=(disc_count > 0),
            discrepancy_count=disc_count,
            latitude=location.latitude if location else None,
            longitude=location.longitude if location else None,
            boundary_geojson=location.boundary_geojson if location else None,
            geometry_validation_status=location.geometry_validation_status if location else "UNVERIFIED",
            map_source=location.map_source if location else "NONE"
        )

gis_service = GisService()
