# SIH26018 Live Demo Runbook

**Presenter:** Samuel Morris  
**Audience:** Smart India Hackathon (SIH) Evaluation Panel  
**System:** Intelligent Land Record Digitization and Validation System  

---

## 1. Before Demo (Setup Checklist)

Open 3 Windows PowerShell terminals and run:

### Terminal 1: Database
```powershell
cd C:\Users\samue\OneDrive\Desktop\hackathon\SIH26018
docker compose up -d
docker compose ps
```
*Verify container `sih26018_postgres` is healthy.*

### Terminal 2: Backend API
```powershell
cd C:\Users\samue\OneDrive\Desktop\hackathon\SIH26018\backend
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe scripts\prepare_demo.py
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Verify `Application startup complete` on port `8000`.*

### Terminal 3: Frontend Web Portal
```powershell
cd C:\Users\samue\OneDrive\Desktop\hackathon\SIH26018\frontend
npm run dev
```
*Verify Vite running on `http://127.0.0.1:5173`.*

---

## 2. Login

1. Open your browser and navigate to: **`http://127.0.0.1:5173`**
2. In the Revenue Authentication Gateway, enter the Chief Revenue Commissioner (Admin) demo credentials:
   * **Email:** `admin@revenue.gov.in`
   * **Password:** `AdminPass123!`
3. Click **Sign In**.
4. Point out the authenticated dashboard showing real-time statistics (total records, validated records, pending reviews, active discrepancies).

---

## 3. Demo Flow 1 — Clean Record Digitization (Happy Path)

**Goal:** Demonstrate high-accuracy OCR extraction, Indian revenue terminology parsing, and automatic validation.

1. In the sidebar, click **Upload Document**.
2. Document Type: Select **Jamabandi / Record of Rights**.
3. Choose File: Select:
   `backend\tests\fixtures\sample_documents\clean_land_record.png`
4. Click **Upload & Process Document**.
5. **What to point out to the judges:**
   * **Asynchronous Execution:** The document is immediately accepted, queued into an asynchronous processing job, and executed without UI blocking.
   * **Native OCR Engine:** Powered locally by Tesseract OCR v5.5.3 (no external cloud dependency, fully offline capable for secure government intranets).
   * **Extracted Fields Table:** Show the extracted revenue fields:
     * Khasra No: `104/2`
     * Khata No: `45`
     * Registered Owner: `Ram Prasad Sharma`
     * Co-Owners: `Shyam Prasad Sharma`
     * Land Area: `1.2500 ha`
     * Classification: `Agricultural`
     * Village: `Bairagarh`, Tehsil: `Huzur`, District: `Bhopal`
   * **Confidence Score:** High confidence badge (`0.95` / `HIGH`).
   * **Deterministic Validation Gates:** Point out the 5 passing rules:
     * Required administrative fields check
     * Permissible area sanity check
     * Khasra format syntax check
     * Confidence threshold evaluation
     * Standardized land classification check
   * **Status:** The record transitions to `VALIDATED` with `0 Discrepancies`.

---

## 4. Demo Flow 2 — Fraud & Conflict Detection (Discrepancy Engine)

**Goal:** Demonstrate automated detection of counterfeit claims, encroachments, area inflation, and ownership disputes.

1. Click **Upload Document** again.
2. Select File:
   `backend\tests\fixtures\sample_documents\conflicting_land_record.png`
3. Click **Upload & Process Document**.
4. Navigate to the **Discrepancies** or **Record Detail** view.
5. **What to point out to the judges:**
   * **Automated Cross-Verification:** The system immediately flags conflicting claims against the existing canonical title in the database.
   * **Flagged Issues & Severity Levels:**
     * `OWNER_MISMATCH` (**Severity: HIGH**): Unverified claim by `Vikram Aditya Singh` against the established owner `Ram Prasad Sharma`.
     * `AREA_MISMATCH` (**Severity: CRITICAL**): Claimed area `3.5000 ha` vs actual registered area `1.2500 ha` (divergence exceeds permissible `0.01 ha` tolerance).
     * `SURVEY_CONFLICT` (**Severity: HIGH**): Unlawful classification shift from `Agricultural` to `Commercial`.
     * `CO_OWNER_MISMATCH` (**Severity: MEDIUM**): Unmatched parties in title transfer.
     * `DUPLICATE_DOCUMENT` (**Severity: MEDIUM**): Duplicate submission alert for the same parcel.
   * **Review Workflow:** The record is automatically marked as `FLAGGED` and routed to the Sub-Divisional Magistrate (Reviewer) queue rather than being accepted blindly.

---

## 5. GIS / Cadastral Map Demonstration

**Goal:** Show interactive spatial representation of land parcels using standardized GeoJSON boundaries.

1. In the sidebar, click **Cadastral Map**.
2. Select **District: Bhopal** or **Village: Bairagarh**.
3. **What to point out to the judges:**
   * **Interactive Visual Map:** Interactive Leaflet map displaying real polygon parcel boundaries and centroid pins.
   * **Spatial Status Color-Coding:** Validated parcels appear green, while disputed/flagged parcels with discrepancies appear amber/red.
   * **Parcel Inspection Drawer:** Click on parcel `104/2` to display its linked record summary, ownership history, and area metrics.

---

## 6. PDF Verification Report Generation

**Goal:** Demonstrate tamper-evident, point-in-time official documentation.

1. On the detail view of record `104/2`, click **Download Verification Report** (or call `/records/{id}/verification-report`).
2. Open the downloaded PDF (`verification_report_104_2_*.pdf`).
3. **What to point out to the judges:**
   * Professional point-in-time governmental verification report generated dynamically via ReportLab.
   * Contains official title headers, administrative jurisdiction, parcel metrics, OCR confidence summary, and formal verification timestamp.

---

## 7. Audit Trail & Governance

**Goal:** Show complete transparency and tamper-evident administrative accountability.

1. In the sidebar, click **Audit Logs** (or navigate to `/audit`).
2. **What to point out to the judges:**
   * Every action in the system is recorded in an append-only, immutable PostgreSQL log (`audit_logs` table).
   * Displays exact timestamps, action types (`DOCUMENT_UPLOADED`, `JOB_COMPLETED`, `DISCREPANCIES_DETECTED`, `REPORT_GENERATED`), target entity UUIDs, and the authenticated user identity.

---

## 8. Role-Based Access Control (RBAC) Quick Demo

**Goal:** Prove strict security boundaries between operational roles.

1. Click **Logout**.
2. Log in as Citizen Viewer:
   * **Email:** `viewer_demo@revenue.gov.in`
   * **Password:** `ViewerDemoPass123!`
3. Note that the Citizen Viewer can view validated records and the Cadastral Map, but cannot upload documents, trigger OCR, approve records, or inspect admin audit logs.

---

## 9. Key Judge Talking Points (Memorize These)

* **1. Offline & Sovereign Capability:** "SIH26018 operates entirely within secure government intranet infrastructure. Native Tesseract OCR and deterministic rules run offline without sending sensitive citizen data to external third-party APIs."
* **2. Deterministic Verification vs Hallucination:** "We use strict, deterministic rule-based verification gates for area sanity, Khasra syntax, and survey classifications. Land records demand mathematical precision, not generative guesswork."
* **3. Proactive Fraud Detection:** "The system doesn't merely digitize text—it continuously cross-references incoming documents against the active land registry, instantly flagging area inflation, ownership conflicts, and illegal land classification conversions."
* **4. Human-in-the-Loop Governance:** "Algorithms flag anomalies; revenue officers make final legal determinations. Our RBAC workflow ensures every action is accountable and immutably audited."
* **5. Spatial Multi-Dimensionality:** "By binding tabular land records directly to cadastral GeoJSON polygons, we eliminate ghost plots and streamline dispute resolution."
