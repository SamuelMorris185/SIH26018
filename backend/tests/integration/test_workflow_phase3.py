import io
import os
import uuid
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

def test_document_upload_privacy(client: TestClient):
    """Verifies that uploaded documents do not expose server-side filesystem paths."""
    res = client.post(
        "/api/v1/documents",
        files={"file": ("jamabandi_bhopal_2026.pdf", io.BytesIO(b"%PDF content"), "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    assert res.status_code == 201
    data = res.json()

    # file_path must NOT be present in public response
    assert "file_path" not in data
    # storage_key must be present and safe
    assert "storage_key" in data
    assert data["storage_key"].endswith(".pdf")
    assert "/" not in data["storage_key"]
    assert "\\" not in data["storage_key"]

def test_document_process_and_record_upsert(client: TestClient):
    """
    Tests POST /api/v1/documents/{id}/process and verifies that reprocessing
    updates the existing record rather than creating duplicate records.
    """
    # 1. Upload document
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("survey_khasra_register.pdf", io.BytesIO(b"%PDF valid register bytes"), "application/pdf")},
        data={"doc_type": "KHASRA_RECORD"}
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 2. Process document via POST /api/v1/documents/{id}/process
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == 200, proc_res.text
    proc_data = proc_res.json()
    assert len(proc_data["records"]) == 1
    record_id = proc_data["records"][0]["id"]

    # 3. Check document records count
    doc_recs_res = client.get(f"/api/v1/documents/{doc_id}/records")
    assert doc_recs_res.status_code == 200
    assert len(doc_recs_res.json()) == 1

    # 4. Reprocess document
    reproc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert reproc_res.status_code == 200
    reproc_data = reproc_res.json()
    assert len(reproc_data["records"]) == 1
    # Verify the same record ID was updated, not duplicated
    assert reproc_data["records"][0]["id"] == record_id

    # Count must remain 1
    doc_recs_res2 = client.get(f"/api/v1/documents/{doc_id}/records")
    assert len(doc_recs_res2.json()) == 1

def test_record_validation_endpoints(client: TestClient):
    """Tests GET /records/{id}/validation and POST /records/{id}/validate."""
    # Create record
    create_res = client.post(
        "/api/v1/records",
        json={
            "state": "Madhya Pradesh",
            "district": "Ujjain",
            "tehsil": "Ghatiya",
            "village": "Panbihar",
            "khasra_number": "120/1",
            "khata_number": "52",
            "area_in_hectares": 1.75
        }
    )
    assert create_res.status_code == 201
    record_id = create_res.json()["id"]

    # Trigger manual validation via POST /records/{id}/validate
    val_post_res = client.post(f"/api/v1/records/{record_id}/validate")
    assert val_post_res.status_code == 200
    val_data = val_post_res.json()
    assert val_data["record_id"] == record_id
    assert val_data["is_valid"] is True
    assert val_data["status"] == "VALIDATED"

    # Query latest validation via GET /records/{id}/validation
    val_get_res = client.get(f"/api/v1/records/{record_id}/validation")
    assert val_get_res.status_code == 200
    assert val_get_res.json()["record_id"] == record_id
    assert val_get_res.json()["status"] == "VALIDATED"

def test_upload_rejection_security(client: TestClient):
    """Tests 415 rejection for unsupported extension and MIME types."""
    # 1. Reject disallowed extension (.exe)
    res_exe = client.post(
        "/api/v1/documents",
        files={"file": ("trojan.exe", io.BytesIO(b"executable payload"), "application/octet-stream")}
    )
    assert res_exe.status_code == 415
    assert res_exe.json()["status"] == "error"

    # 2. Reject disallowed MIME type (text/plain)
    res_txt = client.post(
        "/api/v1/documents",
        files={"file": ("notes.txt", io.BytesIO(b"plain text notes"), "text/plain")}
    )
    assert res_txt.status_code == 415
    assert res_txt.json()["status"] == "error"

def test_missing_physical_file_handling(client: TestClient):
    """Verifies that missing physical storage files return 404 and update document to FAILED."""
    # 1. Upload valid document
    res = client.post(
        "/api/v1/documents",
        files={"file": ("ghost_file.pdf", io.BytesIO(b"%PDF content"), "application/pdf")}
    )
    assert res.status_code == 201
    doc_id = res.json()["id"]

    # 2. Simulate physical file deletion behind the scenes
    from app.services.storage_service import storage_service
    # Find and delete file in storage
    for p in storage_service.base_dir.iterdir():
        if p.is_file():
            p.unlink()

    # 3. Trigger processing -> Must fail gracefully with 404
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == 404
    assert proc_res.json()["status"] == "error"

    # 4. Check document status was transitioned to FAILED
    doc_check = client.get(f"/api/v1/documents/{doc_id}")
    assert doc_check.status_code == 200
    assert doc_check.json()["status"] == "FAILED"

def test_flagged_validation_workflow(client: TestClient):
    """Verifies that extraction with discrepancies properly marks document & record as FLAGGED."""
    # Upload document with trigger name 'discrepancy_scan.pdf'
    res = client.post(
        "/api/v1/documents",
        files={"file": ("discrepancy_scan.pdf", io.BytesIO(b"%PDF simulated discrepancy"), "application/pdf")}
    )
    assert res.status_code == 201
    doc_id = res.json()["id"]

    # Process document
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == 200
    data = proc_res.json()

    # Both document and record must be FLAGGED
    assert data["document"]["status"] == "FLAGGED"
    assert len(data["records"]) == 1
    assert data["records"][0]["status"] == "FLAGGED"
    assert data["validations"][0]["is_valid"] is False
    assert "FLAGGED" in data["summary"]
