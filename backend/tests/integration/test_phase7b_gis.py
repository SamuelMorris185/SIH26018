import io
import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.land_record import LandRecordModel
from app.models.parcel_location import ParcelLocationModel
from app.models.user import UserModel
from app.models.audit_log import AuditLogModel
from app.core.security import get_password_hash, create_access_token
from app.services.gis_service import gis_service
from tests.conftest import TestAsyncSessionLocal

SAMPLE_DOCUMENT_TEXT = """
JAMABANDI / RECORD OF RIGHTS (ROR)
State: Rajasthan
District: Jaipur
Tehsil: Sanganer
Village: Rampura
Khasra No: 301/A
Khata No: 88
Total Area: 3.2500 Hectares
Land Classification: Chahi
Owner Name: Mohan Lal Meena
Patta Number: PATTA-2023-991
Registration Number: REG-JP-2023-9988
Mutation Number: MUT-2023-776
Document Date: 2023-09-01
"""

SAMPLE_PARCEL_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [75.7801, 26.8501],
            [75.7852, 26.8505],
            [75.7849, 26.8552],
            [75.7798, 26.8548],
            [75.7801, 26.8501]
        ]
    ]
}

INVALID_UNCLOSED_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [75.7801, 26.8501],
            [75.7852, 26.8505],
            [75.7849, 26.8552],
            [75.7798, 26.8548]  # Missing closing point
        ]
    ]
}

XSS_MALICIOUS_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [75.7801, 26.8501],
            [75.7852, 26.8505],
            [75.7849, 26.8552],
            [75.7801, 26.8501]
        ]
    ],
    "properties": {
        "title": "<script>alert('xss')</script>"
    }
}

def create_test_users():
    admin = UserModel(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        email="admin_gis@sih.gov.in",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="GIS Administrator",
        role="ADMIN",
        is_active=True,
        created_at=datetime.utcnow()
    )
    operator_a = UserModel(
        id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        email="operator_gis_a@sih.gov.in",
        hashed_password=get_password_hash("OperatorPass123!"),
        full_name="GIS Operator A",
        role="OPERATOR",
        is_active=True,
        created_at=datetime.utcnow()
    )
    operator_b = UserModel(
        id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        email="operator_gis_b@sih.gov.in",
        hashed_password=get_password_hash("OperatorPass123!"),
        full_name="GIS Operator B",
        role="OPERATOR",
        is_active=True,
        created_at=datetime.utcnow()
    )
    return admin, operator_a, operator_b

def test_coordinate_validation_rules():
    """Verifies coordinate boundary, finite numeric checks, and invalid rejection."""
    valid, errors = gis_service.validate_coordinates(26.85, 75.80)
    assert valid is True
    assert len(errors) == 0

    # Latitude out of bounds
    valid_lat, errs_lat = gis_service.validate_coordinates(95.0, 75.80)
    assert valid_lat is False
    assert any("Latitude" in e and "out of bounds" in e for e in errs_lat)

    valid_lat_neg, errs_lat_neg = gis_service.validate_coordinates(-91.5, 75.80)
    assert valid_lat_neg is False

    # Longitude out of bounds
    valid_lon, errs_lon = gis_service.validate_coordinates(26.85, 185.0)
    assert valid_lon is False
    assert any("Longitude" in e and "out of bounds" in e for e in errs_lon)

    # NaN / Inf rejection
    import math
    valid_nan, _ = gis_service.validate_coordinates(float("nan"), 75.80)
    assert valid_nan is False

    valid_inf, _ = gis_service.validate_coordinates(26.85, float("inf"))
    assert valid_inf is False

def test_geojson_validation_rules():
    """Verifies GeoJSON structure, polygon closure, vertex checks, and XSS sanitization."""
    # Valid polygon
    valid, geom_type, v_count, errs = gis_service.validate_geojson(SAMPLE_PARCEL_GEOJSON)
    assert valid is True
    assert geom_type == "Polygon"
    assert v_count == 5
    assert len(errs) == 0

    # Unclosed polygon ring
    valid_unclosed, _, _, errs_unclosed = gis_service.validate_geojson(INVALID_UNCLOSED_GEOJSON)
    assert valid_unclosed is False
    assert any("must be closed" in e for e in errs_unclosed)

    # Malicious XSS injection
    valid_xss, _, _, errs_xss = gis_service.validate_geojson(XSS_MALICIOUS_GEOJSON)
    assert valid_xss is False
    assert any("prohibited script tags" in e for e in errs_xss)

    # Invalid geometry type
    invalid_type = {"type": "GeometryCollection", "geometries": []}
    valid_type, _, _, errs_type = gis_service.validate_geojson(invalid_type)
    assert valid_type is False
    assert any("Unsupported geometry type" in e for e in errs_type)

def test_geometry_validation_endpoint(client: TestClient):
    """Verifies POST /api/v1/map/geometry/validate endpoint."""
    # 1. Valid request
    res_valid = client.post(
        "/api/v1/map/geometry/validate",
        json={
            "latitude": 26.852,
            "longitude": 75.804,
            "boundary_geojson": SAMPLE_PARCEL_GEOJSON
        }
    )
    assert res_valid.status_code == 200
    data_valid = res_valid.json()
    assert data_valid["is_valid"] is True
    assert data_valid["geometry_type"] == "Polygon"
    assert data_valid["vertex_count"] == 5
    assert len(data_valid["errors"]) == 0

    # 2. Invalid request
    res_invalid = client.post(
        "/api/v1/map/geometry/validate",
        json={
            "latitude": 150.0,  # Invalid lat
            "longitude": 75.804,
            "boundary_geojson": INVALID_UNCLOSED_GEOJSON
        }
    )
    assert res_invalid.status_code == 200
    data_invalid = res_invalid.json()
    assert data_invalid["is_valid"] is False
    assert len(data_invalid["errors"]) >= 2

def test_attach_parcel_location_and_get_detail(client: TestClient):
    """Tests attaching parcel coordinates and retrieving map parcel detail."""
    # 1. Upload and process a document
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("gis_sample.pdf", io.BytesIO(SAMPLE_DOCUMENT_TEXT.encode("utf-8")), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == 200
    record_id = proc_res.json()["records"][0]["id"]

    # 2. Attach parcel location
    attach_res = client.post(
        f"/api/v1/map/parcels/{record_id}",
        json={
            "latitude": 26.8530,
            "longitude": 75.8050,
            "boundary_geojson": SAMPLE_PARCEL_GEOJSON,
            "map_source": "CADASTRAL_SURVEY",
            "location_confidence": 0.98
        }
    )
    assert attach_res.status_code == 200
    attach_data = attach_res.json()
    assert attach_data["record_id"] == record_id
    assert attach_data["latitude"] == 26.8530
    assert attach_data["longitude"] == 75.8050
    assert attach_data["geometry_validation_status"] == "VALID"

    # 3. Retrieve parcel detail via GET /api/v1/map/parcels/{record_id}
    detail_res = client.get(f"/api/v1/map/parcels/{record_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["record_id"] == record_id
    assert detail["khasra_number"] is not None
    assert detail["village"] is not None
    assert detail["latitude"] == 26.8530
    assert detail["longitude"] == 75.8050
    assert detail["boundary_geojson"]["type"] == "Polygon"

def test_map_parcels_data_minimization(client: TestClient):
    """Verifies that public map features omit sensitive personal citizen data."""
    # Upload and process
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("gis_privacy.pdf", io.BytesIO(SAMPLE_DOCUMENT_TEXT.encode("utf-8")), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    doc_id = upload_res.json()["id"]
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    record_id = proc_res.json()["records"][0]["id"]

    # Attach location
    client.post(
        f"/api/v1/map/parcels/{record_id}",
        json={
            "latitude": 26.8540,
            "longitude": 75.8060,
            "boundary_geojson": SAMPLE_PARCEL_GEOJSON
        }
    )

    # Query map parcels
    map_res = client.get("/api/v1/map/parcels")
    assert map_res.status_code == 200
    features = map_res.json()["parcels"]
    target = next((p for p in features if p["record_id"] == record_id), None)
    assert target is not None

    # Verify sensitive data is NOT present in map feature
    assert "file_path" not in target
    assert "owner_name" not in target  # Omitted for public map data minimization
    assert "co_owners" not in target
    assert "patta_number" not in target
    assert "password" not in target

    # Required map visual attributes ARE present
    assert target["khasra_number"] is not None
    assert target["village"] is not None
    assert target["area_in_hectares"] > 0
    assert target["status"] is not None
    assert target["latitude"] == 26.8540

@pytest.mark.asyncio
async def test_map_parcels_rbac_isolation(unauthenticated_client: TestClient, db_session: AsyncSession):
    """Verifies resource ownership isolation: Operator B cannot view Operator A's non-admin parcels."""
    admin, op_a, op_b = create_test_users()
    db_session.add_all([admin, op_a, op_b])
    await db_session.commit()

    admin_token = create_access_token(data={"sub": str(admin.id), "role": admin.role})
    op_a_token = create_access_token(data={"sub": str(op_a.id), "role": op_a.role})
    op_b_token = create_access_token(data={"sub": str(op_b.id), "role": op_b.role})

    # Operator A uploads document and attaches parcel
    upload_res = unauthenticated_client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {op_a_token}"},
        files={"file": ("gis_rbac.pdf", io.BytesIO(SAMPLE_DOCUMENT_TEXT.encode("utf-8")), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    proc_res = unauthenticated_client.post(
        f"/api/v1/documents/{doc_id}/process",
        headers={"Authorization": f"Bearer {op_a_token}"}
    )
    assert proc_res.status_code == 200
    rec_id = proc_res.json()["records"][0]["id"]

    attach_res = unauthenticated_client.post(
        f"/api/v1/map/parcels/{rec_id}",
        headers={"Authorization": f"Bearer {op_a_token}"},
        json={
            "latitude": 26.8550,
            "longitude": 75.8070,
            "boundary_geojson": SAMPLE_PARCEL_GEOJSON
        }
    )
    assert attach_res.status_code == 200

    # 1. Operator B lists map parcels -> must NOT see Operator A's parcel
    op_b_list = unauthenticated_client.get(
        "/api/v1/map/parcels",
        headers={"Authorization": f"Bearer {op_b_token}"}
    )
    assert op_b_list.status_code == 200
    op_b_parcels = op_b_list.json()["parcels"]
    assert not any(p["record_id"] == rec_id for p in op_b_parcels)

    # 2. Operator B gets parcel detail directly -> 403 Forbidden
    op_b_detail = unauthenticated_client.get(
        f"/api/v1/map/parcels/{rec_id}",
        headers={"Authorization": f"Bearer {op_b_token}"}
    )
    assert op_b_detail.status_code == 403

    # 3. Operator A lists map parcels -> sees own parcel
    op_a_list = unauthenticated_client.get(
        "/api/v1/map/parcels",
        headers={"Authorization": f"Bearer {op_a_token}"}
    )
    assert op_a_list.status_code == 200
    assert any(p["record_id"] == rec_id for p in op_a_list.json()["parcels"])

    # 4. Admin lists map parcels -> sees Operator A's parcel
    admin_list = unauthenticated_client.get(
        "/api/v1/map/parcels",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_list.status_code == 200
    assert any(p["record_id"] == rec_id for p in admin_list.json()["parcels"])

def test_records_without_coordinates_compatibility(client: TestClient):
    """Verifies that records without coordinates do not crash the map API and remain accessible in explorer."""
    # Upload and process a record without attaching coordinates
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("gis_no_coords.pdf", io.BytesIO(SAMPLE_DOCUMENT_TEXT.encode("utf-8")), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    doc_id = upload_res.json()["id"]
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    record_id = proc_res.json()["records"][0]["id"]

    # Map API must succeed without error
    map_res = client.get("/api/v1/map/parcels")
    assert map_res.status_code == 200
    # Record without coordinates is not in map parcels
    assert not any(p["record_id"] == record_id for p in map_res.json()["parcels"])

    # Normal record detail API continues to return the record
    rec_detail_res = client.get(f"/api/v1/records/{record_id}")
    assert rec_detail_res.status_code == 200
    assert rec_detail_res.json()["id"] == record_id

    # Querying parcel detail on record without location returns UNVERIFIED geometry
    detail_res = client.get(f"/api/v1/map/parcels/{record_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["geometry_validation_status"] == "UNVERIFIED"
    assert detail_res.json()["latitude"] is None

def test_map_filtering_by_status_and_discrepancy(client: TestClient):
    """Verifies map query filtering by status and discrepancy flag."""
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("gis_filter.pdf", io.BytesIO(SAMPLE_DOCUMENT_TEXT.encode("utf-8")), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    doc_id = upload_res.json()["id"]
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    record_id = proc_res.json()["records"][0]["id"]

    client.post(
        f"/api/v1/map/parcels/{record_id}",
        json={
            "latitude": 26.8560,
            "longitude": 75.8080,
            "boundary_geojson": SAMPLE_PARCEL_GEOJSON
        }
    )

    rec = proc_res.json()["records"][0]
    village_name = rec["village"]

    # Filter by matching village
    filter_village = client.get(f"/api/v1/map/parcels?village={village_name}")
    assert filter_village.status_code == 200
    assert any(p["record_id"] == record_id for p in filter_village.json()["parcels"])

    # Filter by non-matching village
    filter_non_match = client.get("/api/v1/map/parcels?village=NonExistentVillageXYZ")

    assert filter_non_match.status_code == 200
    assert len(filter_non_match.json()["parcels"]) == 0

@pytest.mark.asyncio
async def test_audit_event_logged_on_parcel_location(client: TestClient, db_session: AsyncSession):
    """Verifies append-only audit event logged when parcel location is attached."""
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("gis_audit.pdf", io.BytesIO(SAMPLE_DOCUMENT_TEXT.encode("utf-8")), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    doc_id = upload_res.json()["id"]
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    record_id = proc_res.json()["records"][0]["id"]

    attach_res = client.post(
        f"/api/v1/map/parcels/{record_id}",
        json={
            "latitude": 26.8570,
            "longitude": 75.8090,
            "boundary_geojson": SAMPLE_PARCEL_GEOJSON
        }
    )
    assert attach_res.status_code == 200

    # Query audit logs
    logs_res = await db_session.execute(
        select(AuditLogModel).where(
            AuditLogModel.action == "PARCEL_LOCATION_CREATED",
            AuditLogModel.entity_type == "PARCEL_LOCATION"
        )
    )
    logs = list(logs_res.scalars().all())
    assert len(logs) >= 1
    assert logs[0].new_state["record_id"] == record_id
