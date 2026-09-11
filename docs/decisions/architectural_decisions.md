# Architectural Decision Records (ADR) — SIH26018

## ADR 001: Mandatory Technology Stack Selection

### Context
SIH26018 requires an enterprise-ready foundation for land record digitization, serving citizens, revenue officers, and system administrators with high reliability.

### Decision
We select:
- **Frontend**: React + Vite + TypeScript. Provides fast compilation, strict typing, and high UI performance.
- **Backend**: Python + FastAPI. Offers asynchronous async/await support, Pydantic type validation, automatic OpenAPI doc generation, and seamless ecosystem compatibility for future AI/OCR integrations.
- **Database**: PostgreSQL. Industry standard relational database for spatial data integrity, strict constraints, and transaction safety.

### Consequences
High developer productivity, strict type safety between frontend and backend, clean separation of concerns.

---

## ADR 002: Modular Service Layer Pattern

### Context
Business logic, such as data validation rules and extraction parsing, must not be tightly coupled to FastAPI HTTP routing handlers.

### Decision
Encapsulate all business rules inside dedicated Service classes (`DigitizationService`, `ValidationService`). Route handlers only perform request parsing, delegate execution to services, and return typed responses.

### Consequences
Allows high unit testability without running HTTP servers, and enables future CLI or queue-based execution of the same service logic.
