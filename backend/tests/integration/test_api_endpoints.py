import io
import uuid
import pytest
from fastapi.testclient import TestClient

def test_documents_api(client: TestClient):
    # 1. Register document
    res = client.post(
        "/api/v1/documents",
        files={"file": ("khasra_sample.pdf", io.BytesIO(b"pdf content"), "application/pdf")},
        data={"doc_type": "KHASRA_RECORD"}
    )
    assert res.status_code == 201
    doc_id = res.json()["id"]

    # 2. List documents
    list_res = client.get("/api/v1/documents", params={"page": 1, "limit": 10})
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 3. Get single document
    get_res = client.get(f"/api/v1/documents/{doc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["file_name"] == "khasra_sample.pdf"

    # 4. Missing document returns 404
    missing_id = uuid.uuid4()
    not_found_res = client.get(f"/api/v1/documents/{missing_id}")
    assert not_found_res.status_code == 404
    assert not_found_res.json()["status"] == "error"

def test_upload_and_process_convenience_endpoint(client: TestClient):
    res = client.post(
        "/api/v1/digitization/upload-and-process",
        files={"file": ("quick_doc.pdf", io.BytesIO(b"quick content"), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    assert res.status_code == 201
    data = res.json()
    assert "document" in data
    assert "records" in data
    assert len(data["records"]) == 1

def test_records_crud_and_patch(client: TestClient):
    # 1. Create manual record
    payload = {
        "state": "Madhya Pradesh",
        "district": "Indore",
        "tehsil": "Depalpur",
        "village": "Betma",
        "khasra_number": "55/1",
        "khata_number": "30",
        "area_in_hectares": 2.15,
        "land_classification": "Agricultural"
    }
    create_res = client.post("/api/v1/records", json=payload)
    assert create_res.status_code == 201
    record_id = create_res.json()["id"]

    # 2. Get record
    get_res = client.get(f"/api/v1/records/{record_id}")
    assert get_res.status_code == 200
    assert get_res.json()["district"] == "Indore"

    # 3. Patch record
    patch_res = client.patch(
        f"/api/v1/records/{record_id}",
        json={"area_in_hectares": 2.45, "status": "VALIDATED"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["area_in_hectares"] == 2.45
    assert patch_res.json()["status"] == "VALIDATED"

    # 4. Invalid state transition returns 409 Conflict
    invalid_patch = client.patch(
        f"/api/v1/records/{record_id}",
        json={"status": "EXTRACTED"}
    )
    assert invalid_patch.status_code == 409
    assert "cannot transition from 'VALIDATED' to 'EXTRACTED'" in invalid_patch.json()["message"]

    # 5. Missing record returns 404
    fake_id = uuid.uuid4()
    missing_res = client.get(f"/api/v1/records/{fake_id}")
    assert missing_res.status_code == 404

def test_validation_endpoints(client: TestClient):
    # Create record
    create_res = client.post(
        "/api/v1/records",
        json={
            "state": "Rajasthan",
            "district": "Jaipur",
            "tehsil": "Sanganer",
            "village": "Muhana",
            "khasra_number": "701",
            "khata_number": "14",
            "area_in_hectares": 0.85
        }
    )
    record_id = create_res.json()["id"]

    # Run validation endpoint
    val_res = client.post(f"/api/v1/validation/records/{record_id}")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["record_id"] == record_id
    assert val_data["is_valid"] is True
    assert val_data["status"] == "VALIDATED"

    # Get validation history
    hist_res = client.get(f"/api/v1/validation/records/{record_id}/history")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 1
    assert history[0]["status"] == "VALIDATED"

def test_search_endpoint(client: TestClient):
    # Seed a record
    client.post(
        "/api/v1/records",
        json={
            "state": "Gujarat",
            "district": "Ahmedabad",
            "tehsil": "Daskroi",
            "village": "Bareja",
            "khasra_number": "999/A",
            "khata_number": "500",
            "area_in_hectares": 3.50,
            "land_classification": "Commercial"
        }
    )

    # Search by village
    search_res = client.get("/api/v1/search", params={"village": "bareja"})
    assert search_res.status_code == 200
    data = search_res.json()
    assert data["total"] >= 1
    assert any(r["khasra_number"] == "999/A" for r in data["data"])

    # Search with no matches
    empty_res = client.get("/api/v1/search", params={"state": "NonExistentState"})
    assert empty_res.status_code == 200
    assert empty_res.json()["total"] == 0
