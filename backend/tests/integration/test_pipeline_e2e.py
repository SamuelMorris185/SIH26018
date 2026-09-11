import io
import uuid
import pytest
from fastapi.testclient import TestClient

def test_full_digitization_pipeline_e2e(client: TestClient):
    """
    Tests the complete end-to-end processing pipeline via real API endpoints:
    1. Upload document -> 2. Process through pipeline -> 3. Verify record & validation -> 4. Search query
    """
    # Step 1: Upload a scanned Jamabandi document
    file_content = b"%PDF-1.4 Simulated Revenue Register Content for Bhopal Huzur Tehsil"
    file_obj = io.BytesIO(file_content)
    
    upload_res = client.post(
        "/api/v1/documents",
        files={"file": ("jamabandi_bhopal_sample.pdf", file_obj, "application/pdf")},
        data={"doc_type": "JAMABANDI"}
    )
    assert upload_res.status_code == 201, upload_res.text
    doc_data = upload_res.json()
    doc_id = doc_data["id"]
    assert doc_data["status"] == "UPLOADED"
    assert doc_data["file_name"] == "jamabandi_bhopal_sample.pdf"

    # Step 2: Trigger the Digitization Processing Pipeline
    pipeline_res = client.post(f"/api/v1/digitization/process/{doc_id}")
    assert pipeline_res.status_code == 200, pipeline_res.text
    pipeline_data = pipeline_res.json()

    # Verify pipeline response components
    assert pipeline_data["document"]["id"] == doc_id
    assert pipeline_data["document"]["status"] in {"EXTRACTED", "VALIDATED"}
    assert pipeline_data["extraction"]["document_id"] == doc_id
    assert pipeline_data["extraction"]["provider"] == "MOCK_OCR_V1"
    assert len(pipeline_data["records"]) == 1
    assert len(pipeline_data["validations"]) == 1

    created_record = pipeline_data["records"][0]
    record_id = created_record["id"]
    assert created_record["document_id"] == doc_id
    # Check normalized values
    assert created_record["state"] == "Madhya Pradesh"
    assert created_record["district"] == "Bhopal"
    assert created_record["tehsil"] == "Huzur"
    assert created_record["khasra_number"] == "104/2"
    assert created_record["area_in_hectares"] == 1.25

    # Step 3: Retrieve record by ID with validation details
    record_res = client.get(f"/api/v1/records/{record_id}")
    assert record_res.status_code == 200
    record_detail = record_res.json()
    assert record_detail["id"] == record_id
    assert record_detail["latest_validation"] is not None
    assert record_detail["latest_validation"]["is_valid"] is True

    # Step 4: Verify document -> records relationship endpoint
    doc_records_res = client.get(f"/api/v1/documents/{doc_id}/records")
    assert doc_records_res.status_code == 200
    records_list = doc_records_res.json()
    assert len(records_list) == 1
    assert records_list[0]["id"] == record_id

    # Step 5: Query via Search Service
    search_res = client.get(
        "/api/v1/search",
        params={
            "district": "bhopal",
            "khasra_number": "104",
            "status": created_record["status"]
        }
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] >= 1
    matching = [r for r in search_data["data"] if r["id"] == record_id]
    assert len(matching) == 1
