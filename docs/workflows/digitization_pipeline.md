# Land Record Digitization Pipeline Specification — SIH26018 (Phase 4)

## 1. Overview

The digitization pipeline is the core processing engine of the SIH26018 platform. It converts physical land revenue records into structured, validated, and human-reviewable land records with end-to-end auditability and role-based access control.

---

## 2. Pipeline Lifecycle & Governance Stages

```mermaid
sequenceDiagram
    autonumber
    actor Officer as Authenticated Operator / Admin
    participant DocAPI as Documents API (RBAC)
    participant Storage as LocalStorageService
    participant Coordinator as DigitizationService
    participant OCR as MockExtractionProvider
    participant Normalizer as NormalizationService
    participant RecordSvc as LandRecordService
    participant ValEngine as ValidationEngine
    participant Audit as AuditService
    participant DB as PostgreSQL Database
    actor Reviewer as Reviewer / Admin

    Officer->>DocAPI: POST /api/v1/documents (Upload binary + metadata)
    Note over DocAPI: Validate JWT, Role (Admin/Operator), MIME, Size <= 10MB
    DocAPI->>Storage: save_file(file_bytes)
    Storage-->>DocAPI: (storage_path, file_size)
    DocAPI->>DB: INSERT Document (status='UPLOADED', created_by=user_id)
    DocAPI->>Audit: log_event('DOCUMENT_CREATED')
    DocAPI-->>Officer: 201 Created (DocumentResponse with storage_key)

    Officer->>DocAPI: POST /api/v1/documents/{document_id}/process
    Note over DocAPI: Verify Ownership / Permissions
    DocAPI->>Coordinator: execute_pipeline(document_id)
    Coordinator->>Storage: file_exists(file_path)?
    Coordinator->>DB: UPDATE Document (status='PROCESSING')

    Coordinator->>Storage: read_file(file_path)
    Coordinator->>OCR: extract_document_fields(...)
    OCR-->>Coordinator: RawExtractionPayload (provider='MOCK_OCR_V1')
    Coordinator->>DB: INSERT ExtractionResultModel
    Coordinator->>DB: UPDATE Document (status='EXTRACTED')

    Coordinator->>Normalizer: normalize_record_data(raw_fields)
    Normalizer-->>Coordinator: Canonical normalized dict

    alt Record exists for Document (Reprocessing Upsert)
        Coordinator->>RecordSvc: update_record(existing_id, normalized_data)
        Coordinator->>Audit: log_event('RECORD_UPDATED')
    else New Land Record
        Coordinator->>RecordSvc: create_record(created_by, review_status='PENDING_REVIEW')
        Coordinator->>Audit: log_event('RECORD_CREATED')
    end

    Coordinator->>ValEngine: evaluate_record(record_id, record_dict)
    ValEngine-->>Coordinator: ValidationCheckResponse (VALIDATED or FLAGGED)
    Coordinator->>DB: INSERT ValidationResultModel
    Coordinator->>Audit: log_event('RECORD_VALIDATED' / 'RECORD_FLAGGED')

    Coordinator->>ComparisonSvc: compare_record(record_id)
    Note over ComparisonSvc: Match Parcel Identity (Village, Tehsil, Khasra)
    ComparisonSvc->>DB: INSERT RecordComparisonModel & DiscrepancyModel
    alt Discrepancies Detected (CRITICAL / HIGH)
        ComparisonSvc->>Coordinator: Discrepancies Found (Auto-Flag Record)
        Coordinator->>DB: UPDATE LandRecord (status='FLAGGED')
        Coordinator->>Audit: log_event('DISCREPANCIES_DETECTED')
    end

    Coordinator->>DB: UPDATE Document (VALIDATED or FLAGGED)
    Coordinator->>Audit: log_event('DOCUMENT_PROCESSED')

    Note over Reviewer: Hand-off to Human Review & Discrepancy Governance
    Reviewer->>DB: Inspect Discrepancies (GET /records/{id}/discrepancies)
    Reviewer->>DB: Update Discrepancy (PATCH /discrepancies/{id} -> RESOLVED)
    Reviewer->>DB: POST /records/{id}/approve OR reject
    Reviewer->>Audit: log_event('RECORD_APPROVED' / 'RECORD_REJECTED')
```

---

## 3. Separation of Machine Validation & Human Approval

- **Automated Validation**: Rule-based checks (`AreaSanityRule`, `KhasraFormatRule`, etc.) determine technical data consistency (`VALIDATED` vs `FLAGGED`).
- **Human Review**: Domain expert inspection determines administrative and legal validity (`PENDING_REVIEW` -> `IN_REVIEW` -> `APPROVED` or `REJECTED`).
- **Discrepancy Resolution**: Flagged records must be inspected and approved by a qualified Reviewer or Admin before final revenue synchronization.
