# API Specification — SIH26018 (Phase 4)

**Base URL**: `/api/v1`  
**Authentication**: Bearer Token in `Authorization: Bearer <token>` header (JWT HMAC-SHA256).

---

## 1. Authentication & Access Control

### `POST /api/v1/auth/login`
- **Description**: Authenticates user credentials and issues a signed JWT access token.
- **Access**: Public
- **Request Body**:
  ```json
  {
    "email": "revenue.admin@sih.gov.in",
    "password": "SecurePassword123!"
  }
  ```
- **Responses**:
  - `200 OK`: `TokenResponse` (`access_token`, `token_type`, `expires_in`, `user`)
  - `401 Unauthorized`: `"Invalid email or password."`

### `GET /api/v1/auth/me`
- **Description**: Retrieves profile of the currently authenticated user.
- **Access**: Authenticated (`ADMIN`, `OPERATOR`, `REVIEWER`, `VIEWER`)
- **Responses**:
  - `200 OK`: `UserResponse` (`id`, `email`, `full_name`, `role`, `is_active`, `created_at`)
  - `401 Unauthorized`: If token missing, invalid, or expired

### `POST /api/v1/auth/users`
- **Description**: Creates a new user with an assigned role.
- **Access**: `ADMIN` only
- **Request Body**:
  ```json
  {
    "email": "patwari.bhopal@sih.gov.in",
    "full_name": "Suresh Sharma",
    "role": "OPERATOR",
    "password": "InitialPassword123!"
  }
  ```
- **Responses**:
  - `201 Created`: `UserResponse`
  - `403 Forbidden`: Non-admin callers
  - `409 Conflict`: If email already exists

### `GET /api/v1/auth/users`
- **Description**: Lists paginated users.
- **Access**: `ADMIN` only
- **Response**: `200 OK` (Array of `UserResponse`)

### `PATCH /api/v1/auth/users/{user_id}`
- **Description**: Updates user role or active status.
- **Access**: `ADMIN` only
- **Response**: `200 OK` (`UserResponse`)

---

## 2. Documents Domain

### `POST /api/v1/documents`
- **Description**: Upload a new land document binary (multipart/form-data).
- **Access**: `ADMIN`, `OPERATOR`
- **Security Validations**:
  - Max size: 10MB (`413 Payload Too Large`)
  - Supported extensions: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.tif` (`415 Unsupported Media Type`)
  - Supported MIME types: `application/pdf`, `image/png`, `image/jpeg`, `image/tiff`
  - Path traversal blocked; storage containment verified.
- **Response**: `201 Created` (`DocumentResponse` with redacted `storage_key`, `created_by`)

### `GET /api/v1/documents`
- **Description**: Retrieve paginated list of uploaded documents.
- **Access**: All Authenticated

### `GET /api/v1/documents/{document_id}`
- **Description**: Fetch safe metadata for a specific document.
- **Access**: `ADMIN`, `REVIEWER`, `VIEWER`, or `OPERATOR` (own documents only)

### `POST /api/v1/documents/{document_id}/process`
- **Description**: Explicitly triggers the complete land-record processing workflow on a registered document.
- **Access**: `ADMIN`, `OPERATOR` (own documents only)
- **Response**: `200 OK` (`DigitizationPipelineResult`)

### `GET /api/v1/documents/{document_id}/records`
- **Description**: Retrieves all land records extracted from a specific document.
- **Access**: All Authenticated

---

## 3. Digitization Pipeline

### `POST /api/v1/digitization/upload-and-process`
- **Description**: Single-step upload and immediate pipeline execution convenience endpoint.
- **Access**: `ADMIN`, `OPERATOR`
- **Response**: `201 Created` (`DigitizationPipelineResult`)

### `POST /api/v1/digitization/process/{document_id}`
- **Description**: Processes an existing document.
- **Access**: `ADMIN`, `OPERATOR` (own documents only)

---

## 4. Land Records Domain

### `GET /api/v1/records`
- **Description**: Retrieve paginated land records with optional geographic and status filters.
- **Access**: All Authenticated

### `GET /api/v1/records/{record_id}`
- **Description**: Fetch a single land record by ID with its latest validation check report.
- **Access**: All Authenticated

### `POST /api/v1/records`
- **Description**: Manually create a land record entry.
- **Access**: `ADMIN`, `OPERATOR`

### `PATCH /api/v1/records/{record_id}`
- **Description**: Update land record fields or modify validation status.
- **Access**: `ADMIN`, `OPERATOR`
- **Enforcement**: Invalid status transitions return `409 Conflict`.

### `GET /api/v1/records/{record_id}/validation`
- **Description**: Retrieve the latest validation audit report for a specific land record.
- **Access**: All Authenticated

### `POST /api/v1/records/{record_id}/validate`
- **Description**: Re-run validation rules on an existing land record and persist audit results.
- **Access**: `ADMIN`, `OPERATOR`

### `GET /api/v1/records/{record_id}/validations`
- **Description**: Retrieve complete historical validation audit trail for a land record.
- **Access**: All Authenticated

---

## 5. Human Review & Approval Workflow

### `GET /api/v1/records/{record_id}/review`
- **Description**: Retrieve human review status, notes, rejection reasons, and reviewer attribution.
- **Access**: All Authenticated

### `POST /api/v1/records/{record_id}/submit-review`
- **Description**: Submit land record for human inspection (`IN_REVIEW`).
- **Access**: `ADMIN`, `OPERATOR`, `REVIEWER`

### `POST /api/v1/records/{record_id}/approve`
- **Description**: Formally approve a land record (`APPROVED`).
- **Access**: `ADMIN`, `REVIEWER` (Operators and Viewers receive `403 Forbidden`)

### `POST /api/v1/records/{record_id}/reject`
- **Description**: Reject a land record with mandatory `rejection_reason` (min 5 chars).
- **Access**: `ADMIN`, `REVIEWER` (Operators and Viewers receive `403 Forbidden`)

---

## 6. Validation Engine

### `POST /api/v1/validation/records/{record_id}`
- **Description**: Executes modular rule verification on an existing land record.
- **Access**: `ADMIN`, `OPERATOR`

### `GET /api/v1/validation/records/{record_id}/history`
- **Description**: Retrieves verification audit trail for the given record.
- **Access**: All Authenticated

---

## 7. Search & Query

### `GET /api/v1/search`
- **Description**: Advanced multi-criteria search executing directly against database.
- **Access**: All Authenticated

---

## 8. Auditability & Governance

### `GET /api/v1/audit-logs`
- **Description**: Retrieve immutable system audit trail with filters (actor, action, entity type, entity ID, date).
- **Access**: `ADMIN` only (`403 Forbidden` for other roles)

---

## 9. Extraction Inspection & Cross-Record Discrepancy Detection (Phase 5)

### `GET /api/v1/records/{record_id}/extraction`
- **Description**: Retrieves structured OCR extraction result, field-level confidences, categories (HIGH/MEDIUM/LOW), and raw extraction evidence.
- **Access**: All Authenticated (Operator ownership enforced)
- **Response**: `200 OK` (`ExtractionResultResponse`)

### `GET /api/v1/records/{record_id}/discrepancies`
- **Description**: Lists all discrepancies detected for a given land record.
- **Access**: All Authenticated (Operator ownership enforced)
- **Response**: `200 OK` (Array of `DiscrepancyResponse`)

### `POST /api/v1/records/{record_id}/compare`
- **Description**: Triggers deterministic parcel comparison against existing registry records. Idempotent.
- **Access**: `ADMIN`, `OPERATOR`
- **Response**: `200 OK` (`ComparisonSummaryResponse`)

### `GET /api/v1/records/{record_id}/comparisons`
- **Description**: Retrieves historical comparison match pairings for the record.
- **Access**: All Authenticated (Operator ownership enforced)
- **Response**: `200 OK` (Array of `RecordComparisonResponse`)

### `PATCH /api/v1/discrepancies/{discrepancy_id}`
- **Description**: Updates discrepancy lifecycle status (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`, `DISMISSED`) with resolution notes.
- **Access**: `ADMIN`, `REVIEWER` (Operators and Viewers receive `403 Forbidden`)
- **Response**: `200 OK` (`DiscrepancyResponse`)

