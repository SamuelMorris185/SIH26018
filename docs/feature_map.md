# Feature Map & Module Specifications — SIH26018

## Overview Feature Taxonomy

```
Core Features
├── Document Ingestion & Image Preprocessing
├── OCR & NLP Extraction Engine
├── Land Record Classification & Mapping
└── Automated Validation & Discrepancy Detection

Supporting Features
├── User Authentication & RBAC Management
├── Verification Dashboard & Manual Overrides
├── Audit Logging & Historical Tracking
└── Health Monitoring & System Diagnostics
```

---

## Detailed Feature Specifications

### 1. Document Ingestion & Image Preprocessing
- **Purpose**: Upload and preprocess physical scanned land registers, Jamabandi, and cadastral maps.
- **User Roles**: Revenue Officer, Data Operator
- **Input**: PDF, PNG, JPG, TIFF document uploads
- **Processing**: Format validation, resolution check, auto-rotation, noise reduction.
- **Output**: Preprocessed document stored with a `document_id`.
- **Database Entities**: `documents`, `users`
- **API Requirements**: `POST /api/v1/digitize/upload`
- **Frontend Requirements**: Drag-and-drop file uploader with progress tracking.
- **Dependencies**: File Storage system.

---

### 2. OCR & NLP Extraction Engine
- **Purpose**: Extract key revenue fields from handwritten and printed records in Indian languages.
- **User Roles**: System Automated Pipeline
- **Input**: Preprocessed `document_id`
- **Processing**: Field extraction (Owner Name, Father/Husband Name, Khasra No, Khata No, Area in Hectares, Land Type), confidence scoring per field.
- **Output**: Unvalidated `LandRecord` entity with field-level confidence scores.
- **Database Entities**: `documents`, `land_records`, `record_owners`
- **API Requirements**: `POST /api/v1/digitize/extract/{document_id}`
- **Frontend Requirements**: Side-by-side document image preview vs extracted field form.
- **Dependencies**: OCR service abstraction layer.

---

### 3. Automated Validation & Discrepancy Detection
- **Purpose**: Validate extracted data against deterministic business rules and historical records.
- **User Roles**: Revenue Officer, System Pipeline
- **Input**: Extracted `record_id`
- **Processing**: Runs rule checks:
  - `AREA_SANITY_CHECK`: Verifies plot area is positive and within village boundaries.
  - `KHASRA_FORMAT_CHECK`: Verifies land parcel numbering pattern.
  - `OWNER_SHARE_TOTAL_CHECK`: Verifies ownership shares sum to 100%.
  - `DUPLICATE_RECORD_CHECK`: Detects conflicting ownership claims on same survey number.
- **Output**: Validation status (`VALIDATED` vs `FLAGGED`), detailed discrepancy report.
- **Database Entities**: `land_records`, `validation_audits`
- **API Requirements**: `POST /api/v1/validate/record/{id}`
- **Frontend Requirements**: Validation status indicator badges, discrepancy alert panel.
- **Dependencies**: Rule Engine service.

---

### 4. Verification Dashboard & Manual Overrides
- **Purpose**: Allow Revenue Officers to review flagged extractions, correct OCR errors, and manually validate records.
- **User Roles**: Revenue Officer, Admin
- **Input**: User edits on extracted record fields, approval/rejection commands.
- **Processing**: Updates record status, logs manual override action in audit trail.
- **Output**: Updated `LandRecord` with status `VALIDATED` or `REJECTED`.
- **Database Entities**: `land_records`, `validation_audits`, `users`
- **API Requirements**: `PATCH /api/v1/records/{id}`, `POST /api/v1/validate/override`
- **Frontend Requirements**: Interactive editable record form, override audit comment modal.
- **Dependencies**: RBAC User permissions.

---

### 5. Health Monitoring & System Diagnostics
- **Purpose**: Continuous operational monitoring of backend services and database connectivity.
- **User Roles**: System Admin, Developer, CI/CD
- **Input**: Periodic HTTP GET requests
- **Processing**: Checks service state, memory, DB pool health.
- **Output**: JSON status payload.
- **Database Entities**: None
- **API Requirements**: `GET /`, `GET /health`
- **Frontend Requirements**: Real-time system health status widget on Dashboard.
- **Dependencies**: FastAPI core router.
