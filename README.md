# SIH26018

## Intelligent Land Record Digitization and Validation System

### 1. Overview

SIH26018 turns scanned land records into searchable structured records and helps
operators identify missing information, inconsistent parcel details, and conflicting
ownership claims. Reviewers inspect the evidence and record approval or rejection.
It is a hackathon prototype; automated results are not legal title certification.

### 2. Key Features

- JWT login and ADMIN, OPERATOR, REVIEWER, and VIEWER roles.
- PDF, PNG, JPEG, and TIFF uploads with a 10 MB default limit and protected previews.
- Local Tesseract OCR, image preprocessing, field extraction, and confidence evidence.
- Explicit MOCK mode for demonstrations without OCR; outputs identify the mock provider.
- Record normalization, search, rule validation, and cross-record discrepancy detection.
- Human review, discrepancy resolution, and application audit events.
- Persistent job status and retries, with execution inside the FastAPI process.
- Leaflet parcel maps using stored coordinates and GeoJSON boundaries.
- Downloadable PDF verification summaries.

### 3. System Architecture

```text
User -> React / Vite frontend -> FastAPI REST API -> JWT / RBAC
                                    |
                 Upload -> Local file storage -> OCR / field extraction
                                    |
                    Normalization -> Validation -> Record comparison
                                    |
                     PostgreSQL <- Review decisions / Audit events
                                    |
                          GIS map / PDF reports
```

SQLAlchemy uses asyncpg at runtime. Alembic uses psycopg2 for migrations.
Background jobs use asyncio tasks; PostgreSQL stores their status.

### 4. Technology Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 18, Vite 5, TypeScript, Leaflet |
| API | Python, FastAPI, Pydantic 2 |
| Persistence | SQLAlchemy 2, Alembic, PostgreSQL 16 |
| Authentication | PyJWT, bcrypt |
| OCR / documents | Tesseract, pytesseract, Pillow, pypdf |
| Reports | ReportLab |
| Verification | pytest, HTTPX, SQLite tests, disposable PostgreSQL checks |

### 5. Project Structure

```text
SIH26018/
  frontend/src/          # Pages, components, contexts, API client, types
  backend/app/           # API routes, models, schemas, services, configuration
  backend/scripts/       # Development seeds and PostgreSQL verification
  backend/tests/         # Unit, integration, and synthetic OCR fixtures
  database/migrations/   # Alembic environment and revision chain
  database/seeds/        # Compatibility seed entry point
  docs/                  # Earlier design notes and implementation documents
  scripts/               # Development utilities
  docker-compose.yml     # PostgreSQL 16 only
```

The source and this README describe the current implementation. Some older phase
notes under `docs/` describe planned or superseded behavior.

### 6. Prerequisites

- Python 3.10+ and Node.js 22+ with npm.
- Docker Desktop running Linux containers, or an existing PostgreSQL 16 instance.
- Tesseract on PATH for real OCR and the full backend test suite; English language
  data is required. Alternatively set `TESSERACT_CMD_PATH` in `backend/.env`.
- Verify with `python --version`, `node --version`, `docker version`,
  `tesseract --version`, and `tesseract --list-langs`.

### 7. Quick Start

Use **Windows PowerShell**. Steps 8 and 9 start the application when you are ready;
migration and test commands do not start development servers.

1. Clone your repository or open the existing checkout. Enter the directory that
   contains `docker-compose.yml` (in this workspace, `cd .\SIH26018`).

2. Copy the environment templates once, keeping any existing local configuration:

   ```powershell
   Copy-Item .env.example .env
   Copy-Item backend\.env.example backend\.env
   Copy-Item frontend\.env.example frontend\.env
   ```

   Root `.env` configures Docker only. Backend settings come from `backend/.env`;
   Vite reads `frontend/.env`. Set `OCR_ENGINE=TESSERACT` for real extraction, or
   retain `MOCK` for explicitly simulated data. Generate a private JWT secret:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Set the result as `JWT_SECRET_KEY` in `backend/.env`. The default database URL
   matches Compose. If changing credentials or port, update both configurations.

3. Start PostgreSQL and confirm it is healthy:

   ```powershell
   docker compose up -d postgres
   docker compose ps
   ```

4. Create and activate the backend virtual environment:

   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use `.\venv\Scripts\python.exe` in place
   of `python` in the following commands.

5. Install backend dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

6. Create/update the database schema through Alembic:

   ```powershell
   python -m alembic upgrade head
   python -m alembic current
   ```

7. Seed the development accounts:

   ```powershell
   python scripts/seed_demo_data.py
   ```

   This requires migrations at head and `APP_ENV=development`. Existing users,
   passwords, roles, and active status remain unchanged.

8. Start FastAPI in this backend terminal:

   ```powershell
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

9. In a second PowerShell terminal, enter `SIH26018/frontend`:

   ```powershell
   npm ci
   npm run dev
   ```

10. Open the frontend at [http://127.0.0.1:5173](http://127.0.0.1:5173).
    API: [http://127.0.0.1:8000](http://127.0.0.1:8000).
    Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

After ingesting records, `python scripts/seed_cadastral_parcels.py` from `backend`
adds **synthetic demonstration boundaries** where locations are missing. It requires
an active admin and marks new locations `DEMO_SYNTHETIC`; these are not surveyed plots.
`python scripts/demo_phase5.py` runs the real OCR demonstration against the migrated
development database and adds demo documents, records, and review events.

### 8. Demo Accounts

**DEVELOPMENT/DEMO ONLY — never use these credentials in production.**

| Role | Email | Password |
| --- | --- | --- |
| ADMIN | admin@revenue.gov.in | AdminPass123! |
| OPERATOR | operator_demo@revenue.gov.in | OperatorDemoPass123! |
| REVIEWER | reviewer_demo@revenue.gov.in | ReviewerDemoPass123! |
| VIEWER | viewer_demo@revenue.gov.in | ViewerDemoPass123! |

These credentials apply to newly seeded accounts. Rerunning the seed does not reset
an existing account.

### 9. API Documentation

[Swagger UI](http://127.0.0.1:8000/docs) exposes the live OpenAPI schema. Login accepts
JSON at `POST /api/v1/auth/login`; send its token as `Authorization: Bearer <token>`.
API groups include documents, records, digitization, validation, discrepancies,
review, jobs, map, audit logs, and system diagnostics.

### 10. Database / Migrations

Run from `backend`:

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic heads
python -m alembic history
python -m alembic revision --autogenerate -m "Describe schema change"
```

Review generated migrations before applying them. The linear chain is
`001 -> 002 -> 003 -> 004 -> 005 -> 006_safe_user_role_default`.
Existing revision IDs are unchanged. The migration environment creates or widens
`alembic_version.version_num` to PostgreSQL `TEXT`, permanently accommodating
`003_phase5_extraction_discrepancies` without manual database edits.
Revision 006 corrects the default for newly created users to VIEWER; it does not
change existing role assignments. Seeds never create the schema.

### 11. Testing

Backend, from its activated environment:

```powershell
python -m compileall -q app scripts ../database/migrations
python -m pytest -q
python -m pip check
python scripts/verify_postgres.py
```

The pytest suite uses isolated SQLite storage; real OCR tests require Tesseract.
The PostgreSQL script requires CREATE DATABASE permission on the configured server.
It creates and removes a uniquely named disposable database, checks fresh and legacy
migrations, schema/model agreement, offline SQL, real OCR persistence, PDF generation,
concurrent job enqueueing, and seeds. It does not migrate the application database.

Frontend, from `frontend`:

```powershell
npm run lint
npx tsc --noEmit
npm run build
```

`lint` currently runs the TypeScript checker; there is no separate ESLint or browser
end-to-end test suite.

### 12. Security Notes

- Signed JWTs require subject, issue-time, and expiry claims; RBAC uses the active
  database user. Passwords are salted bcrypt hashes, limited to 72 UTF-8 bytes.
- Operator record/document access is limited to owned or unassigned resources.
  ADMIN, REVIEWER, and VIEWER can read records; only ADMIN/REVIEWER decide reviews.
  Jobs and GIS currently apply stricter admin/owner access.
- Audit events record authentication, processing, changes, and review actions.
  They are append-only through the API, not cryptographically tamper-proof.
- Replace demo credentials and secrets, configure HTTPS and explicit CORS origins,
  and protect database/storage access before deployment. Non-development settings
  reject the shared development JWT secret.

### 13. Current Limitations

- OCR uses English/Latin-script field patterns; handwriting and regional-language
  extraction are not validated. PDF handling reads text or embedded images, not
  arbitrary full-page rendering. Bigha areas require regional conversion and are
  flagged rather than guessed.
- Jobs execute in the API process; restart recovery and a durable worker queue are
  absent. The upload screen uses synchronous processing with an animated indicator.
- GIS validates basic structure/ranges, not self-intersections, spatial overlap, or
  cadastral accuracy. Basemap tiles and web fonts require internet access.
- Reprocessing/recomparison cannot overwrite terminal review decisions or reviewed
  discrepancies. A reviewed-record amendment workflow is not implemented.
- Browser navigation is held in memory; tokens are stored in localStorage.
  Health endpoints report database configuration, not live database connectivity.
- Reports use standard PDF fonts; regional-script rendering needs further work.

### 14. Future Enhancements

- Durable job workers and restart recovery.
- Regional OCR datasets, extraction evaluation, and regional area-unit support.
- Reviewed-record amendment/versioning and stronger spatial validation.
- Browser workflow tests and deployment hardening.
