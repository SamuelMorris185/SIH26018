# SIH26018 — Intelligent Land Record Digitization and Validation System

**Ministry of Rural Development • Smart India Hackathon 2026**

---

## Executive Summary

**SIH26018** is an enterprise-grade platform designed to digitize legacy handwritten, scanned, and physical land revenue records (Jamabandi, Khasra, Khata registers, cadastral maps) into structured, search-optimized data while enforcing automated discrepancy detection, confidence evaluation, and human review validation audits.

### Core Technology Stack

- **Frontend**: React + Vite + TypeScript (SPA)
- **Backend**: Python 3.10+ • FastAPI • Pydantic v2 • SQLAlchemy 2.0 (Async)
- **OCR Engine**: Local Native Tesseract OCR v5.5.3 (`TESSERACT_OCR_V1`) + Fallback `MOCK_OCR_V1`
- **Vision Preprocessing**: Pillow (`PIL.ImageEnhance.Contrast`, Grayscale, Auto-Rescale, Sharpening)
- **Database**: PostgreSQL 15+ (`asyncpg` runtime, `psycopg2-binary` migrations)
- **Migrations**: Alembic (Revisions `001_phase2_core_domain`, `002_phase4_auth_audit_review`, `003_phase5_extraction_discrepancies`)
- **Testing**: `pytest`, `pytest-asyncio`, `aiosqlite`, `httpx` (78 Passing Tests)

---

## Architecture & Processing Workflow (Phase 5)

```
Physical Document Upload (Authenticated: ADMIN / OPERATOR)
          ↓
[DocumentService & LocalStorageService]  ──>  documents Table (UPLOADED, created_by)
  • Path Traversal Defense                    (Safe storage_key, path redaction)
  • 10MB Max Size (413 Payload Too Large)
  • MIME / Ext Whitelisting (415)
  • Ownership & RBAC Verification
          ↓
[DigitizationService Coordinator]         ──>  Triggered via POST /digitization/process/{id}
          ↓
[Pluggable OCR Engine: Tesseract / Mock]  ──>  extraction_results Table (TESSERACT_OCR_V1)
  • Pillow Image Preprocessing                 (Grayscale, Contrast x1.8, Lanczos Rescaling, Sharpen)
  • Digital & Raster PDF Stream Parsing        (Multi-page pypdf + embedded raster image OCR)
  • Indian Revenue Terminology Variations      (Khasra/Survey/Gat, Khata/Khatoni, Rakba/Area, Mauza, Taluka)
  • Confidence Categorization (HIGH/MED/LOW)   (Structured fields + dual raw/normalized evidence)
          ↓
[NormalizationService]
  • Geographic Casing, Khasra Standards, Area Hectare Parsing, Owner & Co-owner Normalization
          ↓
[LandRecordService]                       ──>  land_records Table (NORMALIZED / VALIDATED / FLAGGED)
                                               (Idempotent Record Upsert on Reprocess)
                                               (Initial Review Status: PENDING_REVIEW)
          ↓
[ValidationEngine]                        ──>  validation_results Table (Single-Record Sanity Audits)
          ↓
[ComparisonService Engine]                ──>  record_comparisons & discrepancies Tables
  • Parcel Identity Resolution                 (State + District + Tehsil + Village + Khasra)
  • Owner Mismatch Detection (Levenshtein)
  • Land Area Divergence Detection (|diff| > 0.01 ha tolerance)
  • Survey Classification & Duplicate Conflicts
  • Low-Confidence Critical Field Auto-Flagging (< 0.60)
          ↓
[Human Review & Governance]               ──>  POST /records/{id}/submit-review (IN_REVIEW)
                                               PATCH /discrepancies/{id} (OPEN -> ACKNOWLEDGED / RESOLVED / DISMISSED)
                                               [HTTP 409 Conflict protection on illegal transitions]
                                               POST /records/{id}/approve (APPROVED - Reviewer/Admin)
                                               POST /records/{id}/reject (REJECTED - Reviewer/Admin)
          ↓
[Immutable Audit Trail]                   ──>  audit_logs Table (Append-Only)
                                               GET /api/v1/audit-logs (Admin Only)
```

---

## Directory Structure

```
SIH26018/
├── frontend/             # React + Vite + TypeScript SPA
├── backend/              # Python FastAPI Application
│   ├── app/
│   │   ├── api/
│   │   │   ├── dependencies/ # auth (get_current_user, require_role)
│   │   │   └── routes/       # auth, documents, digitization, records, review, discrepancies, validation, search, audit, health, system
│   │   ├── core/         # config, security (bcrypt + JWT), logging, exceptions & error handlers
│   │   ├── db/           # async SQLAlchemy session & DeclarativeBase
│   │   ├── models/       # UserModel, DocumentModel, LandRecordModel, ExtractionResultModel, ValidationResultModel, AuditLogModel, RecordComparisonModel, DiscrepancyModel
│   │   ├── schemas/      # Pydantic DTO request/response schemas (user, document, record, review, discrepancy, health)
│   │   └── services/     # UserService, AuditService, ReviewService, DocumentService, DigitizationService, LandRecordService, ComparisonService, NormalizationService
│   │       └── extraction/ # BaseExtractionProvider, MockExtractionProvider, TesseractOCRProvider, Factory
│   ├── tests/
│   │   ├── fixtures/     # Sample synthetic documents (clean PNG, noisy PNG, conflicting PNG, digital PDF, corrupt file)
│   │   ├── unit/         # Security, storage, auth, review, normalization, validation engine, tesseract real OCR, discrepancy transitions
│   │   └── integration/  # E2E pipeline, auth/RBAC API, human review API, audit trail, search tests
│   ├── alembic.ini       # Alembic migrations configuration
│   ├── pytest.ini        # Pytest configuration
│   ├── main.py           # FastAPI application entrypoint
│   └── requirements.txt
├── database/
│   ├── migrations/       # Alembic schema versions (001_phase2_core_domain, 002_phase4_auth_audit_review, 003_phase5_extraction_discrepancies)
│   └── seeds/            # Initial seeding skeletons
├── docker-compose.yml    # Reproducible PostgreSQL 16 container setup
├── docs/                 # Architectural specifications, workflows, security, & API docs
├── scripts/              # Setup & verification utilities
└── README.md
```

---

## Getting Started

### 1. OCR Engine Setup (Tesseract OCR)

**Windows (via Scoop or Winget):**
```powershell
# Recommended: Scoop installs directly to user space without UAC prompts
scoop install tesseract
# Install language models (English, Hindi, OSD)
# Tessdata path: %USERPROFILE%\scoop\apps\tesseract\current\tessdata\
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-hin
```

Verify Tesseract installation:
```bash
tesseract --version
tesseract --list-langs
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive API Docs (Swagger)**: `http://127.0.0.1:8000/docs`
- **System OCR Status Endpoint**: `http://127.0.0.1:8000/api/v1/system/ocr-status`
- **Redoc API Docs**: `http://127.0.0.1:8000/redoc`
- **System Health**: `http://127.0.0.1:8000/health`

### 3. Database & Docker (PostgreSQL)

To run a dedicated PostgreSQL 16 instance via Docker Compose:
```bash
docker compose up -d
```

To run migrations:
```bash
cd backend
alembic upgrade head
```

### 4. Running Phase 5 End-to-End Live Demonstration

Run the automated live demonstration script to visualize the complete flow:
`Upload -> Real Native Tesseract OCR -> Image Preprocessing -> Normalization -> Single-Record Validation -> Cross-Record Discrepancy Detection -> Reviewer Governance & Audit Confirmation`:

```bash
cd backend
python scripts/demo_phase5.py
```

### 5. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://127.0.0.1:5173`.

---

## Running Test Suites

The backend test suite includes 78 unit and integration tests covering OCR availability, real Tesseract raster image execution, preprocessing, regional Indian revenue terminology, confidence scoring boundaries, cross-document comparison idempotency, discrepancy state transitions, RBAC, and human review governance:

```bash
cd backend
pytest -v
```

**Result:** `78 passed in ~16s` (100% pass rate, zero warnings).
