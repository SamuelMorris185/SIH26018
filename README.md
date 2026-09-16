# SIH26018 – Intelligent Land Record Digitization and Validation System

SIH26018 is an automated, tamper-evident land record digitization, cross-verification, and anomaly detection platform designed for Indian revenue administration (Jamabandi, Patta, Mutation, and Record of Rights).

The system integrates local native OCR extraction (Tesseract OCR), deterministic validation engines, spatial cadastral GIS parcel mapping, point-in-time PDF verification reports, and immutable audit governance with Role-Based Access Control (RBAC).

---

## 1. Verified Architecture & Components

```text
       React + Vite Frontend (Port 5173)
                   │  (Reverse Proxy /api)
                   ▼
       FastAPI Application (Port 8000)
    ┌──────────────┴──────────────┐
    ▼                             ▼
PyJWT / RBAC Auth         Digitization Engine
(Admin / Operator /       ├─ Native Tesseract OCR (Pillow Preprocessing)
 Reviewer / Viewer)       ├─ Normalization & Indian Revenue Terminology
                          ├─ Deterministic Validation Rules (5 Gates)
                          ├─ Discrepancy & Fraud Detection
                          ├─ Persistent Background Async Jobs
                          ├─ Cadastral GIS Engine (Leaflet GeoJSON)
                          └─ ReportLab PDF Verification Reports
                                  │
                                  ▼
                   PostgreSQL 16 Database (Port 5432)
                   (Alembic Migrations HEAD: 006)
```

---

## 2. Quick Start Guide (Windows PowerShell)

### Step 0: Prerequisites
- Python 3.10+ (with venv)
- Node.js 20+ (with npm)
- Docker Desktop (for PostgreSQL 16)
- Tesseract OCR (on system PATH or configured via `TESSERACT_CMD_PATH`)

---

### Terminal 1: Infrastructure (Project Root)
```powershell
cd C:\Users\samue\OneDrive\Desktop\hackathon\SIH26018
docker compose up -d
docker compose ps
```
*Confirm that `sih26018_postgres` reports `healthy` on port `5432`.*

---

### Terminal 2: Backend (FastAPI & Database)
```powershell
cd C:\Users\samue\OneDrive\Desktop\hackathon\SIH26018\backend

# Setup environment file if not present
if (!(Test-Path .env)) { Copy-Item .env.example .env }

# Apply all database migrations to HEAD
.\venv\Scripts\python.exe -m alembic upgrade head

# Prepare demo accounts and GIS spatial parcels (idempotent)
.\venv\Scripts\python.exe scripts\prepare_demo.py

# Launch development server
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

### Terminal 3: Frontend (React / Vite)
```powershell
cd C:\Users\samue\OneDrive\Desktop\hackathon\SIH26018\frontend
npm install
npm run dev
```

---

## 3. Application URLs

| Service | URL | Description |
| :--- | :--- | :--- |
| **Web Dashboard** | [http://127.0.0.1:5173](http://127.0.0.1:5173) | Interactive React portal with reverse proxy |
| **Backend API** | [http://127.0.0.1:8000](http://127.0.0.1:8000) | Core REST API service |
| **Health Endpoint** | [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health) | Live system and database health check |
| **Swagger UI** | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | Interactive OpenAPI documentation |
| **ReDoc** | [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) | Alternative structured API reference |

---

## 4. Demo Accounts

> [!WARNING]
> **DEVELOPMENT / HACKATHON DEMO ONLY.**
> **NEVER USE THESE CREDENTIALS IN PRODUCTION.**
> All demo accounts are pre-seeded with bcrypt `$2b$` password hashes.

| Role | Email | Password | Allowed Capabilities |
| :--- | :--- | :--- | :--- |
| **ADMIN** | `admin@revenue.gov.in` | `AdminPass123!` | Full system access, audit logs, user management, record approvals |
| **OPERATOR** | `operator_demo@revenue.gov.in` | `OperatorDemoPass123!` | Document upload, OCR triggering, job monitoring, GIS parcel binding |
| **REVIEWER** | `reviewer_demo@revenue.gov.in` | `ReviewerDemoPass123!` | Verification review, discrepancy resolution, record approval/rejection |
| **VIEWER** | `viewer_demo@revenue.gov.in` | `ViewerDemoPass123!` | Read-only access to validated records and cadastral map views |

---

## 5. Demonstration Test Documents

Test documents are located under `backend/tests/fixtures/sample_documents/`:

| File Name | Purpose | Expected Outcome in Demo |
| :--- | :--- | :--- |
| **`clean_land_record.png`** | Canonical Jamabandi scan (Khasra 104/2, Ram Prasad Sharma, 1.25 ha, Agricultural) | **Clean Extraction:** High confidence (0.95), all 5 validation gates pass, status `VALIDATED`, zero discrepancies. |
| **`conflicting_land_record.png`** | Contested claim on Khasra 104/2 (Vikram Aditya Singh, 3.5 ha, Commercial) | **Fraud/Discrepancy Detection:** Triggers `OWNER_MISMATCH`, `AREA_MISMATCH`, `SURVEY_CONFLICT`, and duplicate detection. Status `FLAGGED`. |
| **`noisy_land_record.png`** | Degraded, low-contrast document | **Confidence Warning:** Low OCR confidence triggers manual operator review flags. |
| **`clean_digital_record.pdf`** | Vector digital PDF land record | **Digital Extraction:** Direct PDF stream text parsing without OCR degradation. |

---

## 6. Automated Testing Commands

Run finite verification checks from PowerShell:

```powershell
# Backend pytest test suite (133 tests)
cd backend
.\venv\Scripts\python.exe -m pytest -q

# Frontend TypeScript check & production build
cd ..\frontend
npm run build
```

---

## 7. Security & Schema Standards
- **Alembic Migration Revisions:** All historical revision identifiers are strictly `VARCHAR(32)` compliant (Head: `006_safe_user_role_default`). Schema ownership belongs exclusively to Alembic.
- **Idempotent Seeding:** `scripts/prepare_demo.py` safely inspects state before inserting, preventing duplicated demo users or parcel location entries.
- **Data Isolation:** Non-admin roles are restricted to viewing only their own submitted documents or publicly accessible validated land titles.
