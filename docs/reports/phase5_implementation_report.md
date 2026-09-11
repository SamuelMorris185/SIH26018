# Phase 5 Implementation Report — SIH26018

**Project**: SIH26018 — Intelligent Land Record Digitization and Validation System  
**Phase**: Phase 5 — Real OCR, Structured Land-Record Extraction, Confidence Handling, and Cross-Record Discrepancy Detection  
**Status**: Completed and Verified  
**Date**: September 11, 2026  

---

## 1. Files Created or Modified

### New Files Created
1. `backend/app/models/discrepancy.py`: `RecordComparisonModel` and `DiscrepancyModel` with composite indexes and cascade rules.
2. `backend/app/schemas/discrepancy.py`: Enums (`DiscrepancyType`, `DiscrepancySeverity`, `DiscrepancyStatus`) and DTOs (`DiscrepancyResponse`, `DiscrepancyUpdate`, `RecordComparisonResponse`, `ComparisonSummaryResponse`).
3. `backend/app/services/extraction/tesseract_provider.py`: `TesseractOCRProvider` (`TESSERACT_OCR_V1`) for local native OCR execution across images and PDF streams.
4. `backend/app/services/extraction/factory.py`: `get_extraction_provider()` resolving providers via `OCR_ENGINE` configuration.
5. `backend/app/services/comparison_service.py`: `ComparisonService` coordinating parcel identity resolution, discrepancy detection rules, idempotent persistence, and lifecycle transitions.
6. `backend/app/api/routes/discrepancies.py`: REST endpoints for discrepancy retrieval, manual comparison triggering, comparison history, and status updates.
7. `database/migrations/versions/003_phase5_extraction_discrepancies.py`: Alembic migration for `record_comparisons`, `discrepancies`, and new structured fields on `land_records` and `extraction_results`.
8. `backend/tests/fixtures/sample_documents/manifest.py`: Synthetic, anonymized sample document fixtures covering clean titles, owner conflicts, area divergences, survey conflicts, low-confidence scans, and duplicate filings.
9. `backend/tests/fixtures/sample_documents/__init__.py`: Package initialization for fixtures.
10. `backend/scripts/demo_phase5.py`: Repeatable CLI demonstration script visualizing the complete flow.
11. `backend/tests/unit/test_extraction_providers.py`: Unit tests for pluggable OCR providers, factory selection, confidence bounds, and error handling.
12. `backend/tests/unit/test_comparison_engine.py`: Unit tests for discrepancy detection rules, parcel matching, and idempotency.
13. `backend/tests/integration/test_discrepancy_api.py`: Integration tests for discrepancy REST endpoints, RBAC permissions, and operator ownership isolation.
14. `backend/tests/integration/test_pipeline_phase5.py`: Integration tests for end-to-end pipeline execution with automatic discrepancy detection and audit logging.
15. `docs/features/cross_record_discrepancy_detection.md`: Comprehensive domain documentation for discrepancy detection.
16. `docs/reports/phase5_implementation_report.md`: This report.

### Existing Files Modified
1. `backend/app/core/config.py`: Added `OCR_ENGINE`, `TESSERACT_CMD_PATH`, confidence thresholds, and area tolerance settings.
2. `backend/app/core/exceptions.py`: Added `OCREngineUnavailableError`, `DiscrepancyNotFoundError`, and `ComparisonError`.
3. `backend/app/models/extraction.py`: Added `structured_fields` and `confidence_category` columns.
4. `backend/app/models/land_record.py`: Added `owner_name`, `co_owners`, `patta_number`, `registration_number`, `mutation_number`, `document_date`, and relationships to `discrepancies` and `comparisons`.
5. `backend/app/schemas/extraction.py`: Added `ConfidenceCategory`, `categorize_confidence`, `FieldExtractionEvidence`, and `StructuredLandRecordExtraction`.
6. `backend/app/schemas/record.py`: Added Phase 5 fields to schemas and included `discrepancies` in `LandRecordDetailResponse`.
7. `backend/app/schemas/pipeline.py`: Added optional `discrepancies` field to `DigitizationPipelineResult`.
8. `backend/app/services/extraction/provider.py`: Extended `BaseExtractionProvider` and updated `MockExtractionProvider` to produce structured fields with evidence.
9. `backend/app/services/extraction/__init__.py`: Exported new providers and factory.
10. `backend/app/services/normalization_service.py`: Added normalizers for names, co-owners, identifiers, and dates.
11. `backend/app/services/land_record_service.py`: Stored Phase 5 structured fields on record creation.
12. `backend/app/services/digitization_service.py`: Integrated pluggable OCR factory, structured persistence, and automated cross-record comparison.
13. `backend/app/api/routes/records.py`: Added `GET /records/{record_id}/extraction` and populated `discrepancies` in detail response.
14. `backend/app/api/router.py`: Registered `discrepancies.router`.
15. `README.md`: Updated architecture diagram, feature summary, test counts, and demo instructions.
16. `docs/api/api_specification.md`: Documented Phase 5 discrepancy and extraction inspection endpoints.
17. `docs/workflows/digitization_pipeline.md`: Updated sequence diagram and workflow documentation.

---

## 2. OCR Provider Implementation Status

| Provider | Identifier | Availability | Description |
|----------|------------|--------------|-------------|
| **Mock Extraction Provider** | `MOCK_OCR_V1` | Always Available | Deterministic simulation provider for offline development, negative condition testing (corrupt, empty), and automated test suites. |
| **Tesseract OCR Provider** | `TESSERACT_OCR_V1` | Environment Dependent | Native offline OCR implementation utilizing `pytesseract` and `pypdf`. Parses raster images (PNG, JPEG, TIFF) and digital PDFs. Gracefully checks binary presence; if unavailable, raises `OCREngineUnavailableError` (503) with actionable setup guidance. |

- **Factory Selection**: Dynamic resolution via `OCR_ENGINE` configuration (`"MOCK"` vs `"TESSERACT"`).
- **Integrity Guarantee**: Never falsely claims simulated extraction is real OCR output; provider identity and extraction version are stored permanently in `extraction_results`.

---

## 3. Extraction Fields Supported

| Canonical Field | Type | Normalized Example | Evidence Extracted |
|----------------|------|--------------------|-------------------|
| `owner_name` | String | `"Ram Prasad Sharma"` | `"Owner: Ram Prasad Sharma"` |
| `co_owners` | Array[String] | `["Shyam Prasad Sharma"]` | `"Co-Owners: Shyam Prasad Sharma"` |
| `khasra_number` | String | `"104/2"` | `"Khasra Number: 104/2"` |
| `khata_number` | String | `"45"` | `"Khata Number: 45"` |
| `patta_number` | String | `"PATTA-2024-889"` | `"Patta No: PATTA-2024-889"` |
| `village` | String | `"Bairagarh"` | `"Village: Bairagarh"` |
| `tehsil` | String | `"Huzur"` | `"Tehsil: Huzur"` |
| `district` | String | `"Bhopal"` | `"District: Bhopal"` |
| `state` | String | `"Madhya Pradesh"` | `"State: Madhya Pradesh"` |
| `area_in_hectares` | Decimal(10,4) | `1.2500` | `"Area: 1.2500 ha"` |
| `area_unit` | String | `"hectare"` | Unit specifier |
| `land_classification` | String | `"Agricultural"` | `"Classification: Agricultural"` |
| `registration_number` | String | `"REG-2024-MP-00123"` | `"Registration No: REG-2024-MP-00123"` |
| `mutation_number` | String | `"MUT-2024-00456"` | `"Mutation No: MUT-2024-00456"` |
| `document_date` | DateTime | `2024-01-15T00:00:00` | `"Date: 2024-01-15"` |

---

## 4. Confidence Implementation

- **Strict Bounding**: Every confidence score is clamped within `[0.0, 1.0]`.
- **Field-Level Granularity**: Individual fields maintain distinct confidence scores and evidence text.
- **Configurable Categorization**:
  - `HIGH`: `>= 0.85`
  - `MEDIUM`: `>= 0.60` and `< 0.85`
  - `LOW`: `< 0.60`
- **Automated Flagging**: Any mandatory field (`khasra_number`, `village`, `district`, `state`, `area_in_hectares`) with `LOW` confidence triggers a `LOW_CONFIDENCE_CRITICAL_FIELD` discrepancy, automatically setting the record to `FLAGGED` and `PENDING_REVIEW`.

---

## 5. Comparison and Discrepancy Rules

Comparison identity resolves existing ground-truth records matching:
`State + District + Tehsil + Village AND Khasra Number (or Khata Number)`.

| Discrepancy Type | Severity | Rule Description | Action on Match |
|------------------|----------|------------------|-----------------|
| `OWNER_MISMATCH` | `CRITICAL` / `HIGH` | Levenshtein string similarity `< 0.80` on conflicting titleholder claims. | Auto-Flags Record |
| `CO_OWNER_MISMATCH` | `MEDIUM` | Symmetric difference on co-owner sets. | Logged & Flagged |
| `AREA_MISMATCH` | `CRITICAL` / `HIGH` | Divergence between incoming area and existing registry exceeds `0.01 ha`. | Auto-Flags Record |
| `SURVEY_CONFLICT` | `HIGH` | Contradictory land classifications (e.g. Agricultural vs Commercial) on same survey parcel. | Auto-Flags Record |
| `DUPLICATE_DOCUMENT` | `MEDIUM` | Identical parcel attributes submitted under separate document IDs. | Logged |
| `IDENTIFIER_CONFLICT` | `HIGH` | Conflicting registration numbers for identical parcel and owner. | Auto-Flags Record |
| `LOW_CONFIDENCE_CRITICAL_FIELD` | `HIGH` | Critical fields extracted with confidence below `0.60`. | Auto-Flags Record |

### Discrepancy Lifecycle:
`OPEN` ──> `ACKNOWLEDGED` ──> `RESOLVED` / `DISMISSED` (governed by Reviewer or Admin).

---

## 6. Database Migration Revision

- **Revision ID**: `003_phase5_extraction_discrepancies`
- **Revises**: `002_phase4_auth_audit_review`
- **Schema Additions**:
  - `extraction_results`: `structured_fields` (JSON), `confidence_category` (VARCHAR(20)).
  - `land_records`: `owner_name` (VARCHAR(255), indexed), `co_owners` (JSON), `patta_number` (VARCHAR(50)), `registration_number` (VARCHAR(100)), `mutation_number` (VARCHAR(100)), `document_date` (TIMESTAMP).
  - `record_comparisons`: Table with foreign keys to `land_records.id`, tracking match type, discrepancy count, highest severity, and comparison timestamp.
  - `discrepancies`: Table with foreign keys to `land_records.id` and `record_comparisons.id`, tracking discrepancy type, severity, description, values, confidence, and status.

---

## 7. New API Endpoints

| Method | Path | Role Required | Description |
|--------|------|---------------|-------------|
| `GET` | `/api/v1/records/{record_id}/extraction` | Authenticated | Retrieve structured OCR extraction results and field-level evidence. |
| `GET` | `/api/v1/records/{record_id}/discrepancies` | Authenticated | List all discrepancies detected for a specific land record. |
| `POST` | `/api/v1/records/{record_id}/compare` | `ADMIN`, `OPERATOR` | Manually trigger cross-document comparison (idempotent). |
| `GET` | `/api/v1/records/{record_id}/comparisons` | Authenticated | Retrieve historical comparison match pairings for a record. |
| `PATCH` | `/api/v1/discrepancies/{discrepancy_id}` | `ADMIN`, `REVIEWER` | Update discrepancy lifecycle status (`ACKNOWLEDGED`, `RESOLVED`, `DISMISSED`). |

---

## 8. Tests Added

14 new unit and integration tests were created, bringing total test count to **64 passing tests**:
- `tests/unit/test_extraction_providers.py`: 5 tests (structured output, factory selection, Tesseract unavailable handling, confidence categorization, corrupt scan rejection).
- `tests/unit/test_comparison_engine.py`: 7 tests (owner mismatch, co-owner mismatch, area tolerance thresholds, survey conflict, duplicate detection, low confidence flagging, idempotent re-comparison).
- `tests/integration/test_discrepancy_api.py`: 1 test covering complete REST API suite, authentication, operator ownership isolation, and reviewer status updates.
- `tests/integration/test_pipeline_phase5.py`: 1 test covering end-to-end pipeline ingestion of baseline, conflicting owner, conflicting area, and idempotent comparison.

---

## 9. Full Test Results

Command executed:
```powershell
venv\Scripts\pytest -v
```

Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
collected 64 items

tests/integration/test_api_endpoints.py::test_documents_api PASSED       [  1%]
tests/integration/test_api_endpoints.py::test_upload_and_process_convenience_endpoint PASSED [  3%]
tests/integration/test_api_endpoints.py::test_records_crud_and_patch PASSED [  4%]
tests/integration/test_api_endpoints.py::test_validation_endpoints PASSED [  6%]
tests/integration/test_api_endpoints.py::test_search_endpoint PASSED     [  7%]
tests/integration/test_audit_and_review_api.py::test_human_review_endpoints_workflow[asyncio] PASSED [  9%]
tests/integration/test_audit_and_review_api.py::test_audit_logs_endpoints[asyncio] PASSED [ 10%]
tests/integration/test_auth_rbac_api.py::test_auth_login_endpoints[asyncio] PASSED [ 12%]
tests/integration/test_auth_rbac_api.py::test_rbac_admin_user_management[asyncio] PASSED [ 14%]
tests/integration/test_auth_rbac_api.py::test_resource_ownership_and_role_restrictions[asyncio] PASSED [ 15%]
tests/integration/test_discrepancy_api.py::test_discrepancy_api_endpoints_and_rbac[asyncio] PASSED [ 17%]
tests/integration/test_pipeline_e2e.py::test_full_digitization_pipeline_e2e PASSED [ 18%]
tests/integration/test_pipeline_phase5.py::test_end_to_end_phase5_pipeline_with_discrepancy_detection[asyncio] PASSED [ 20%]
tests/integration/test_workflow_phase3.py::test_document_upload_privacy PASSED [ 21%]
tests/integration/test_workflow_phase3.py::test_document_process_and_record_upsert PASSED [ 23%]
tests/integration/test_workflow_phase3.py::test_record_validation_endpoints PASSED [ 25%]
tests/integration/test_workflow_phase3.py::test_upload_rejection_security PASSED [ 26%]
tests/integration/test_workflow_phase3.py::test_missing_physical_file_handling PASSED [ 28%]
tests/integration/test_workflow_phase3.py::test_flagged_validation_workflow PASSED [ 29%]
tests/unit/test_auth_security.py::test_password_hashing_and_salting[asyncio] PASSED [ 31%]
tests/unit/test_auth_security.py::test_jwt_token_generation_and_validation[asyncio] PASSED [ 32%]
tests/unit/test_auth_security.py::test_jwt_expired_token_rejection[asyncio] PASSED [ 34%]
tests/unit/test_auth_security.py::test_jwt_malformed_token_rejection[asyncio] PASSED [ 35%]
tests/unit/test_auth_security.py::test_user_service_crud_and_auth[asyncio] PASSED [ 37%]
tests/unit/test_auth_security.py::test_audit_service_append_only[asyncio] PASSED [ 39%]
tests/unit/test_comparison_engine.py::test_owner_mismatch_rule PASSED    [ 40%]
tests/unit/test_comparison_engine.py::test_co_owner_mismatch_rule PASSED [ 42%]
tests/unit/test_comparison_engine.py::test_area_mismatch_rule PASSED     [ 43%]
tests/unit/test_comparison_engine.py::test_survey_conflict_rule PASSED   [ 45%]
tests/unit/test_comparison_engine.py::test_duplicate_document_rule PASSED [ 46%]
tests/unit/test_comparison_engine.py::test_self_record_low_confidence PASSED [ 48%]
tests/unit/test_comparison_engine.py::test_idempotent_comparison_execution PASSED [ 50%]
tests/unit/test_document_service.py::test_document_lifecycle[asyncio] PASSED [ 51%]
tests/unit/test_extraction_providers.py::test_mock_provider_structured_output PASSED [ 53%]
tests/unit/test_extraction_providers.py::test_ocr_provider_selection_factory PASSED [ 54%]
tests/unit/test_extraction_providers.py::test_tesseract_provider_unavailable_handling PASSED [ 56%]
tests/unit/test_extraction_providers.py::test_confidence_bounds_and_categories PASSED [ 57%]
tests/unit/test_extraction_providers.py::test_empty_and_corrupt_rejection PASSED [ 59%]
tests/unit/test_health.py::test_read_root PASSED                         [ 60%]
tests/unit/test_health.py::test_read_health PASSED                       [ 62%]
tests/unit/test_health.py::test_read_api_health PASSED                   [ 64%]
tests/unit/test_land_record_service.py::test_land_record_lifecycle[asyncio] PASSED [ 65%]
tests/unit/test_mock_extraction.py::test_mock_extraction_provider[asyncio] PASSED [ 67%]
tests/unit/test_normalization.py::test_clean_text PASSED                 [ 68%]
tests/unit/test_normalization.py::test_normalize_title PASSED            [ 70%]
tests/unit/test_normalization.py::test_normalize_khasra PASSED           [ 71%]
tests/unit/test_normalization.py::test_normalize_khata PASSED            [ 73%]
tests/unit/test_normalization.py::test_normalize_area PASSED             [ 75%]
tests/unit/test_normalization.py::test_normalize_classification PASSED   [ 76%]
tests/unit/test_normalization.py::test_deterministic_record_normalization PASSED [ 78%]
tests/unit/test_review_service.py::test_review_service_lifecycle_and_transitions[asyncio] PASSED [ 79%]
tests/unit/test_search_service.py::test_search_service[asyncio] PASSED   [ 81%]
tests/unit/test_security_and_storage.py::test_path_traversal_prevention PASSED [ 82%]
tests/unit/test_security_and_storage.py::test_file_exists_and_missing_file_detection PASSED [ 84%]
tests/unit/test_security_and_storage.py::test_oversized_file_rejection[asyncio] PASSED [ 85%]
tests/unit/test_security_and_storage.py::test_mock_extraction_empty_and_corrupt_files[asyncio] PASSED [ 87%]
tests/unit/test_security_and_storage.py::test_mock_extraction_confidence_bounds[asyncio] PASSED [ 89%]
tests/unit/test_security_and_storage.py::test_unsupported_file_type_rejection PASSED [ 90%]
tests/unit/test_validation_engine.py::test_required_fields_rule PASSED   [ 92%]
tests/unit/test_validation_engine.py::test_area_sanity_rule PASSED       [ 93%]
tests/unit/test_validation_engine.py::test_khasra_format_rule PASSED     [ 95%]
tests/unit/test_validation_engine.py::test_confidence_threshold_rule PASSED [ 96%]
tests/unit/test_land_classification_rule PASSED [ 98%]
tests/unit/test_validation_engine.py::test_validation_engine_complete PASSED [100%]

============================= 64 passed in 11.21s =============================
```

---

## 10. Manual Demonstration Results

Executed command:
```powershell
venv\Scripts\python scripts/demo_phase5.py
```

Result:
- Clean baseline title (`clean_jamabandi_record_104_2.pdf`) processed: `VALIDATED`, 0 discrepancies.
- Conflicting ownership claim (`owner_mismatch_record_104_2.pdf`) processed: Automatically detected `OWNER_MISMATCH` [HIGH] and `CO_OWNER_MISMATCH` [MEDIUM], setting record to `FLAGGED` and `PENDING_REVIEW`.
- Area divergence (`area_mismatch_record_104_2.pdf`) processed: Detected `AREA_MISMATCH` [CRITICAL] (difference: 2.50 ha), record auto-flagged.
- Low-confidence scan (`low_confidence_record_104_2.pdf`) processed: Detected `LOW_CONFIDENCE_CRITICAL_FIELD` [HIGH], record auto-flagged.
- Human review governance: Reviewer user initiated review (`IN_REVIEW`), resolved discrepancy (`RESOLVED`), and formally rejected fraudulent title claim with logged audit reason.

---

## 11. Known Limitations

1. **Native Tesseract Host Dependency**: The Tesseract executable is not pre-installed on this Windows host. While `pytesseract`, `pypdf`, and `Pillow` are installed and the abstraction executes cleanly with graceful fallback (`OCREngineUnavailableError`), running real OCR against scanned images requires installing the Tesseract binary (e.g. `winget install UB-Mannheim.TesseractOCR`).
2. **Handwritten Script Parsing**: Tesseract standard models excel on printed and typed documents (Jamabandi, sale deeds, computer registers), but have limited accuracy on cursive or archaic handwritten revenue scripts (Kaithi, Modi, archaic Urdu).
3. **Synchronous Processing**: The pipeline currently executes synchronously within FastAPI worker requests. While suitable for hackathon demonstrations, production deployments with multi-page PDFs should use a background task queue (Celery, ARQ, or Redis Queue).

---

## 12. Recommended Next Phase (Phase 6)

1. **Asynchronous Task Queue**: Offload document OCR and cross-record comparison to an asynchronous worker queue with WebSockets/SSE progress events.
2. **Advanced Handwriting OCR**: Integrate Vision-Language Models (e.g. PaliGemma or LayoutLMv3) for legacy handwritten cadastral and revenue registers.
3. **Frontend Phase 5 Integration**: Add interactive discrepancy inspection cards, side-by-side document comparison viewers, and one-click discrepancy resolution in the React UI.
