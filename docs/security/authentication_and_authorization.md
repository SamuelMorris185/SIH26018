# Authentication, Role-Based Access Control, and Auditability Specification

## Overview

The **SIH26018 Intelligent Land Record Digitization and Validation System** enforces a multi-tier governance model separating automated digitization, machine validation, and authorized human governance.

---

## 1. Authentication Architecture

- **Token Type**: HMAC-SHA256 JSON Web Tokens (`HS256`).
- **Token Delivery**: HTTP `Authorization: Bearer <access_token>` header.
- **Expiry**: Default 1440 minutes (24 hours), configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`.
- **Password Hashing**: Adaptive `bcrypt` with automatic salting. Plaintext passwords are never stored, logged, or exposed in schemas.
- **Credential Protection**: Generic error message (`"Invalid email or password."`) on authentication failure to prevent username enumeration attacks.

### Authentication Endpoints

| Verb | Path | Protected | Access | Description |
|---|---|---|---|---|
| `POST` | `/api/v1/auth/login` | No | Public | Authenticates credentials; returns signed JWT and safe user profile |
| `GET` | `/api/v1/auth/me` | Yes | Authenticated | Retrieves profile of current active user |
| `POST` | `/api/v1/auth/users` | Yes | `ADMIN` only | Creates a new user with specific role |
| `GET` | `/api/v1/auth/users` | Yes | `ADMIN` only | Lists paginated system users |
| `PATCH` | `/api/v1/auth/users/{user_id}` | Yes | `ADMIN` only | Modifies user role or deactivates user |

---

## 2. Role-Based Access Control (RBAC) Matrix

| Action / Capability | `ADMIN` | `OPERATOR` | `REVIEWER` | `VIEWER` |
|---|:---:|:---:|:---:|:---:|
| User Management (`/auth/users`) | Yes | No | No | No |
| View System Audit Logs (`/audit-logs`) | Yes | No | No | No |
| Upload Land Documents (`POST /documents`) | Yes | Yes | No | No |
| Trigger Pipeline (`POST /documents/{id}/process`) | Yes | Yes (Own) | No | No |
| Create Land Record (`POST /records`) | Yes | Yes | No | No |
| Update Land Record Metadata (`PATCH /records/{id}`) | Yes | Yes (Own) | No | No |
| Trigger Re-validation (`POST /records/{id}/validate`) | Yes | Yes | No | No |
| Submit Record for Review (`POST .../submit-review`) | Yes | Yes | Yes | No |
| Approve Land Record (`POST .../approve`) | Yes | No | Yes | No |
| Reject Land Record (`POST .../reject`) | Yes | No | Yes | No |
| Read Records / Validations / Searches | Yes | Yes | Yes | Yes |

---

## 3. Resource Ownership & Isolation Policy

- When an **`OPERATOR`** uploads a document, `created_by` is stamped with the operator's user UUID.
- An Operator can only view, download, or trigger processing on documents where `created_by == current_user.id` (or unassigned seed documents).
- Attempts by an Operator to access another Operator's document or land record returns `403 Forbidden`.
- **`ADMIN`**, **`REVIEWER`**, and **`VIEWER`** roles can view records across all operators to perform audits, reviews, and inspections.

---

## 4. Immutable Append-Only Audit Trail

All security and workflow actions generate immutable log entries in the `audit_logs` table:

```
[Security / Domain Action]
          ↓
[AuditService.log_event()]
  • Sanitizes sensitive keys (passwords, tokens)
  • Stamps Actor User ID, Client IP, and User-Agent
  • Records Previous and New States (JSON)
          ↓
[audit_logs Table] (Append-Only)
          ↓
[GET /api/v1/audit-logs] (ADMIN Access Exclusively)
```

### Audited Event Types:
- **Authentication**: `LOGIN_SUCCESS`, `LOGIN_FAILURE`.
- **User Administration**: `USER_CREATED`, `USER_ROLE_CHANGED`, `USER_DEACTIVATED`.
- **Documents**: `DOCUMENT_CREATED`, `DOCUMENT_UPDATED`, `DOCUMENT_PROCESSED`, `DOCUMENT_PROCESSING_FAILED`.
- **Land Records**: `RECORD_CREATED`, `RECORD_UPDATED`, `RECORD_VALIDATED`, `RECORD_FLAGGED`.
- **Review & Approval**: `RECORD_SUBMITTED_FOR_REVIEW`, `RECORD_APPROVED`, `RECORD_REJECTED`.
