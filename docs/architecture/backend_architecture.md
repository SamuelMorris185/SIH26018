# Backend Architecture — SIH26018 (Phase 2)

## 1. Backend Technology Stack

- **Framework**: FastAPI (Python 3.10+)
- **Server**: Uvicorn ASGI Server
- **Data Validation & Serialization**: Pydantic v2
- **ORM / Persistence**: SQLAlchemy 2.0 (Async enabled)
- **Database Driver**: `asyncpg` (primary) / `psycopg2-binary` (migrations)
- **Migrations**: Alembic
- **Testing**: `pytest`, `pytest-asyncio`, `aiosqlite`, `httpx`

---

## 2. Phase 2 Directory Structure

```
backend/app/
├── api/
│   ├── routes/
│   │   ├── health.py            # System health & diagnostic routes
│   │   ├── documents.py         # Document upload, query & record association routes
│   │   ├── digitization.py      # Digitization pipeline coordinator routes
│   │   ├── records.py           # Land record management, detail & audit routes
│   │   ├── validation.py        # Standalone record verification & history routes
│   │   └── search.py            # Multi-criteria SQL search & pagination routes
│   └── router.py                # APIRouter mounting /api/v1 prefix
├── core/
│   ├── config.py                # Pydantic BaseSettings loading .env
│   ├── logging.py               # Structured logger
│   └── exceptions.py            # Domain exceptions & global HTTP exception handlers
├── db/
│   ├── base.py                  # DeclarativeBase model registry
│   └── session.py               # Async engine & sessionmaker factory
├── models/                      # SQLAlchemy ORM Data Models
│   ├── document.py              # DocumentModel entity
│   ├── land_record.py           # LandRecordModel entity
│   ├── extraction.py            # ExtractionResultModel entity (raw OCR output)
│   ├── validation.py            # ValidationResultModel entity (rule audit logs)
│   └── user.py                  # UserModel entity
├── schemas/                     # Pydantic DTO Request/Response Schemas
│   ├── health.py                # Health check schemas
│   ├── document.py              # Document request & response schemas
│   ├── extraction.py            # Raw OCR payload schemas
│   ├── record.py                # LandRecord schemas & paginated listings
│   ├── validation.py            # Rule validation results & check responses
│   └── pipeline.py              # End-to-end pipeline response schema
└── services/                    # Domain Services Layer
    ├── storage_service.py       # Decoupled file storage (LocalStorageService)
    ├── document_service.py      # Document lifecycle & state management
    ├── normalization_service.py # Deterministic non-destructive cleaning & formatting
    ├── land_record_service.py   # Land record persistence & update operations
    ├── search_service.py        # SQL-level multi-field filtering & pagination
    ├── digitization_service.py  # End-to-end pipeline coordinator
    ├── extraction/              # OCR Provider Abstraction Layer
    │   ├── provider.py          # BaseExtractionProvider & MockExtractionProvider
    │   └── __init__.py
    └── validation/              # Modular Rule-Based Validation Engine
        ├── rules.py             # RequiredFields, AreaSanity, KhasraFormat, etc.
        ├── engine.py            # ValidationEngine runner & report aggregator
        └── __init__.py
```

---

## 3. Domain Workflow Architecture

The Phase 2 backend implements a domain-oriented pipeline:

```
Physical Document Upload
          ↓
[DocumentService & LocalStorageService]  ──>  Documents Table (UPLOADED)
          ↓
[DigitizationService Coordinator]         ──>  Status: PROCESSING
          ↓
[BaseExtractionProvider]                  ──>  ExtractionResults Table (MOCK_OCR_V1)
(Simulated OCR / Extracted Fields)
          ↓
[NormalizationService]
(Whitespace, Title-case, Khasra Standard, Area Parsing)
          ↓
[LandRecordService]                       ──>  LandRecords Table (NORMALIZED)
          ↓
[ValidationEngine]                        ──>  ValidationResults Table (VALIDATED / FLAGGED)
(Area Sanity, Khasra Format, Required Fields, Confidence)
          ↓
[SearchService]                           ──>  Searchable via /api/v1/search & /api/v1/records
```

---

## 4. Key Architectural Guarantees

1. **Storage Decoupling**: Large physical binaries are managed via `BaseStorageService` (`LocalStorageService`), storing relative paths in PostgreSQL rather than bulky binary blobs.
2. **Raw vs Authoritative Data Separation**: Raw OCR extraction is persisted separately in `extraction_results` to maintain auditability. Only normalized and validated records enter `land_records`.
3. **Deterministic Normalization**: Field standardization is non-destructive, deterministic, and independently testable.
4. **Modular Rule Engine**: Business verification rules are self-contained classes conforming to `BaseValidationRule`, enabling straightforward additions of state-specific revenue rules.
5. **SQL-Level Pagination**: Search executes filtered queries directly with SQLAlchemy `where()`, `limit()`, and `offset()` without in-memory dataset loads.
6. **Robust Error Envelope**: All API exceptions produce consistent JSON error payloads:
   ```json
   {
     "status": "error",
     "code": 404,
     "message": "Land record with identifier '...' not found.",
     "details": null
   }
   ```
