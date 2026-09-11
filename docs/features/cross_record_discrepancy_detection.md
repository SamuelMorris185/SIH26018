# Cross-Record Discrepancy Detection & Intelligent Extraction — SIH26018 (Phase 5)

## 1. Architectural Overview

Phase 5 introduces domain intelligence and cross-record consistency checking to the **SIH26018 Intelligent Land Record Digitization and Validation System**.

The platform moves beyond basic optical character recognition and single-record field checking by comparing incoming filings against canonical ground-truth land records registered in the state revenue database.

```
Document Upload (PDF / Scanned Image)
      ↓
[Pluggable OCR Layer] ──> BaseExtractionProvider
   ├── MockExtractionProvider (MOCK_OCR_V1)
   └── TesseractOCRProvider   (TESSERACT_OCR_V1)
      ↓
[Structured Field Extraction] ──> Owner, Co-Owners, Survey/Khasra, Khata, Patta, Area, Dates, Identifiers
      ↓
[Confidence Categorization] ──> HIGH (>=0.85), MEDIUM (0.60-0.85), LOW (<0.60)
      ↓
[Deterministic Normalization] ──> Title Casing, Identifier Standardization, Khasra Formatting
      ↓
[Validation Engine] ──> Core single-record schema & sanity checks
      ↓
[Cross-Record Comparison Engine] ──> Match on Parcel Identity (State + District + Tehsil + Village + Khasra)
      ├── Rule 1: Owner Mismatch (Levenshtein String Similarity < 0.80)
      ├── Rule 2: Co-Owner Mismatch (Symmetric Difference on Co-owner Set)
      ├── Rule 3: Land Area Mismatch (|diff| > 0.01 ha tolerance)
      ├── Rule 4: Survey Conflict (Contradictory land classifications on identical survey parcel)
      ├── Rule 5: Duplicate Document (Identical parcel attributes in different submissions)
      ├── Rule 6: Identifier Conflict (Conflicting registration numbers for identical owner)
      └── Rule 7: Low-Confidence Critical Fields (Mandatory fields with confidence < 0.60)
      ↓
[Discrepancy Persistence & Flagging] ──> discrepancies & record_comparisons tables
      ↓ (Auto-Flag if HIGH or CRITICAL discrepancies detected)
[Human Review Governance] ──> Reviewer Inspection -> Acknowledged -> Resolved / Dismissed
```

---

## 2. Pluggable OCR Engine Architecture

The extraction abstraction allows seamless switching between offline simulated testing and local native OCR execution:

```python
BaseExtractionProvider (Abstract Base Class)
    ├── MockExtractionProvider (provider="MOCK_OCR_V1")
    └── TesseractOCRProvider   (provider="TESSERACT_OCR_V1")
```

### Provider Selection
Configured via `OCR_ENGINE` environment variable in `.env`:
- `OCR_ENGINE=MOCK`: Preserves deterministic, offline test behavior without external runtime dependencies.
- `OCR_ENGINE=TESSERACT`: Leverages local `pytesseract` and `pypdf` engines.
  - Checks executable availability via `tesseract --version` or `TESSERACT_CMD_PATH`.
  - Fails gracefully with `OCREngineUnavailableError` (HTTP 503) if the binary is absent.
  - Never falsely claims simulated data is real OCR output.

---

## 3. Structured Land Record Extraction Schema

Extraction extracts canonical legal and revenue fields along with extraction evidence:

| Field Name | Description | Source Evidence |
|------------|-------------|-----------------|
| `owner_name` | Primary titleholder / Bhumiswami | Snippet e.g. "Owner: Ram Prasad Sharma" |
| `co_owners` | Array of joint titleholders | Extracted co-owner listing |
| `khasra_number` | Unique parcel survey identifier | "Khasra No: 104/2" |
| `khata_number` | Account / Khatoni ledger number | "Khata No: 45" |
| `patta_number` | Lease / land grant number | "Patta No: PATTA-2024-889" |
| `village` | Revenue village (Mauza/Gram) | "Village: Bairagarh" |
| `tehsil` | Sub-district division (Taluk/Tehsil) | "Tehsil: Huzur" |
| `district` | Revenue district | "District: Bhopal" |
| `state` | State jurisdiction | "State: Madhya Pradesh" |
| `area_in_hectares` | Physical parcel size | "Area: 1.2500 ha" |
| `area_unit` | Unit of measure (hectare, acre, bigha) | "hectare" |
| `land_classification` | Agricultural, Residential, Commercial | "Classification: Agricultural" |
| `registration_number` | Deed registry reference | "Registration: REG-2024-MP-00123" |
| `mutation_number` | Revenue mutation entry | "Mutation: MUT-2024-00456" |
| `document_date` | Date of physical document issuance | "Date: 2024-01-15" |

---

## 4. Confidence-Aware Extraction Engine

Confidence scores are strictly bounded within `[0.0, 1.0]`:

- **HIGH** (`confidence >= 0.85`): High optical clarity, clean matching format.
- **MEDIUM** (`0.60 <= confidence < 0.85`): Marginal scan quality or mild OCR ambiguity.
- **LOW** (`confidence < 0.60`): High risk of OCR misinterpretation. Mandatory fields extracted with LOW confidence automatically trigger a `LOW_CONFIDENCE_CRITICAL_FIELD` discrepancy and mark the record `FLAGGED`.

---

## 5. Discrepancy Categories, Severity, and Lifecycle

### Discrepancy Severity Levels:
- `CRITICAL`: High probability of title conflict or fraud (e.g. conflicting owner name, area discrepancy > 1 ha).
- `HIGH`: Conflicting land classifications, registration conflicts, area discrepancy > 0.01 ha.
- `MEDIUM`: Co-owner mismatches, potential duplicate filings.
- `LOW` / `INFO`: Minor formatting or metadata variations.

### Discrepancy Lifecycle:
1. `OPEN`: Newly detected by automated comparison engine.
2. `ACKNOWLEDGED`: Reviewer has examined the discrepancy and opened formal investigation.
3. `RESOLVED`: Discrepancy corrected, explained, or addressed by executive revenue order.
4. `DISMISSED`: Determined to be a benign optical artifact or clerical variance.

---

## 6. Clear Distinction: Deterministic Rules vs AI/LLM

> [!NOTE]
> The discrepancy detection engine implemented in Phase 5 is strictly **deterministic and rule-based**. It utilizes string distance algorithms (Levenshtein, token sort), geographic parcel identity resolution, numerical tolerance intervals, and relational database constraints.
>
> It does **not** rely on Large Language Models (LLMs) or black-box machine learning for basic comparison, ensuring 100% explainability, auditability, and zero hallucination risk for legal land revenue proceedings.

### Future AI/LLM Enhancements (Phase 6+):
- LayoutLMv3 for multi-column complex colonial revenue ledger spatial parsing.
- TrOCR / CRNN models fine-tuned on Modi/Urdu/Devanagari handwritten revenue scripts.
- LLM-assisted multi-document genealogical chain-of-title synthesis.
