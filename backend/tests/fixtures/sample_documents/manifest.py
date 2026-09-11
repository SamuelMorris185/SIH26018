"""
Phase 5 Synthetic Sample Documents Manifest
Provides anonymized, synthetic test fixtures for the SIH26018 Land Record Pipeline.
No real citizen data is utilized.
Covers real Tesseract OCR raster images (PNG), digital PDFs, degraded/noisy scans,
conflicting ownership claims, duplicate filings, and corrupt files.
"""

import os
from typing import Dict, Any

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))

def get_fixture_bytes(filename: str) -> bytes:
    path = os.path.join(FIXTURES_DIR, filename)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    return b""

REAL_OCR_FIXTURES: Dict[str, Dict[str, Any]] = {
    "clean_record_image": {
        "file_name": "clean_land_record.png",
        "mime_type": "image/png",
        "doc_type": "JAMABANDI",
        "ocr_engine": "TESSERACT_OCR_V1",
        "description": "High-resolution clean raster image of canonical land record for Khasra 104/2, Bairagarh.",
        "expected_fields": {
            "state": "Madhya Pradesh",
            "district": "Bhopal",
            "tehsil": "Huzur",
            "village": "Bairagarh",
            "khasra_number": "104/2",
            "khata_number": "45",
            "area_in_hectares": "1.2500 ha",
            "land_classification": "Agricultural",
            "owner_name": "Ram Prasad Sharma",
            "co_owners": "Shyam Prasad Sharma",
            "patta_number": "PATTA-2024-889",
            "registration_number": "REG-2024-MP-00123",
            "mutation_number": "MUT-2024-00456",
            "document_date": "2024-01-15"
        },
        "expected_confidence_range": (0.85, 1.0),
        "expected_confidence_category": "HIGH",
        "expected_status": "VALIDATED",
        "expected_discrepancies": 0
    },
    "noisy_record_image": {
        "file_name": "noisy_land_record.png",
        "mime_type": "image/png",
        "doc_type": "JAMABANDI",
        "ocr_engine": "TESSERACT_OCR_V1",
        "description": "Degraded/blurred image testing low OCR confidence and review trigger.",
        "expected_fields": {
            "khasra_number": "",
            "owner_name": ""
        },
        "expected_confidence_range": (0.0, 0.60),
        "expected_confidence_category": "LOW",
        "expected_status": "FLAGGED",
        "expected_discrepancy_type": "LOW_CONFIDENCE_CRITICAL_FIELD"
    },
    "conflicting_record_image": {
        "file_name": "conflicting_land_record.png",
        "mime_type": "image/png",
        "doc_type": "SALE_DEED",
        "ocr_engine": "TESSERACT_OCR_V1",
        "description": "Raster image with same parcel (104/2) claiming conflicting owner Vikram Aditya Singh.",
        "expected_fields": {
            "state": "Madhya Pradesh",
            "district": "Bhopal",
            "tehsil": "Huzur",
            "village": "Bairagarh",
            "khasra_number": "104/2",
            "khata_number": "45",
            "area_in_hectares": "3.5000 ha",
            "land_classification": "Commercial",
            "owner_name": "Vikram Aditya Singh"
        },
        "expected_status": "FLAGGED",
        "expected_discrepancies": ["OWNER_MISMATCH", "AREA_MISMATCH", "SURVEY_CONFLICT"]
    },
    "duplicate_record_image": {
        "file_name": "duplicate_land_record.png",
        "mime_type": "image/png",
        "doc_type": "JAMABANDI",
        "ocr_engine": "TESSERACT_OCR_V1",
        "description": "Duplicate re-filing of identical attributes for parcel 104/2 under new submission.",
        "expected_status": "VALIDATED",
        "expected_discrepancy_type": "DUPLICATE_DOCUMENT"
    },
    "clean_digital_pdf": {
        "file_name": "clean_digital_record.pdf",
        "mime_type": "application/pdf",
        "doc_type": "JAMABANDI",
        "ocr_engine": "TESSERACT_OCR_V1",
        "description": "Digital PDF with clean embedded text stream.",
        "expected_fields": {
            "state": "Madhya Pradesh",
            "district": "Bhopal",
            "tehsil": "Huzur",
            "village": "Bairagarh",
            "khasra_number": "104/2",
            "khata_number": "45",
            "area_in_hectares": "1.2500 ha",
            "land_classification": "Agricultural",
            "owner_name": "Ram Prasad Sharma"
        },
        "expected_confidence_category": "HIGH",
        "expected_status": "VALIDATED"
    },
    "corrupt_file": {
        "file_name": "corrupt_record.png",
        "mime_type": "image/png",
        "doc_type": "JAMABANDI",
        "ocr_engine": "TESSERACT_OCR_V1",
        "description": "Corrupt binary image that fails gracefully with 422 ExtractionProcessingError.",
        "expected_error": "ExtractionProcessingError"
    }
}

# Preserve backwards compatibility for mock-based test suite
SAMPLE_FIXTURES: Dict[str, Dict[str, Any]] = {
    "clean_record": {
        "file_name": "clean_jamabandi_record_104_2.pdf",
        "doc_type": "JAMABANDI",
        "description": "Baseline canonical land record for Khasra 104/2, Bairagarh, Bhopal.",
        "content": (
            b"%PDF-1.4 [SYNTHETIC LAND RECORD - REVENUE DEPARTMENT]\n"
            b"State: Madhya Pradesh | District: Bhopal | Tehsil: Huzur | Village: Bairagarh\n"
            b"Khasra No: 104/2 | Khata No: 45 | Area: 1.2500 ha | Type: Agricultural\n"
            b"Owner: Ram Prasad Sharma | Co-owner: Shyam Prasad Sharma\n"
            b"Registration No: REG-2024-MP-00123 | Patta No: PATTA-2024-889\n"
        ),
        "expected_status": "VALIDATED",
        "expected_discrepancies": 0
    },
    "owner_mismatch": {
        "file_name": "owner_mismatch_record_104_2.pdf",
        "doc_type": "SALE_DEED",
        "description": "Conflicting ownership claim for parcel 104/2 claiming Vikram Aditya Singh.",
        "content": (
            b"%PDF-1.4 [SYNTHETIC CONFLICT DEED]\n"
            b"State: Madhya Pradesh | District: Bhopal | Tehsil: Huzur | Village: Bairagarh\n"
            b"Khasra No: 104/2 | Khata No: 45 | Area: 1.2500 ha | Type: Agricultural\n"
            b"Owner: Vikram Aditya Singh | Co-owner: Rajesh Kumar\n"
            b"Registration No: REG-2024-MP-00999\n"
        ),
        "expected_status": "FLAGGED",
        "expected_discrepancy_type": "OWNER_MISMATCH",
        "expected_severity": "CRITICAL"
    },
    "area_mismatch": {
        "file_name": "area_mismatch_record_104_2.pdf",
        "doc_type": "JAMABANDI",
        "description": "Divergent land area claim of 3.7500 ha against 1.2500 ha for parcel 104/2.",
        "content": (
            b"%PDF-1.4 [SYNTHETIC AREA DIVERGENCE RECORD]\n"
            b"State: Madhya Pradesh | District: Bhopal | Tehsil: Huzur | Village: Bairagarh\n"
            b"Khasra No: 104/2 | Khata No: 45 | Area: 3.7500 ha | Type: Agricultural\n"
            b"Owner: Ram Prasad Sharma\n"
        ),
        "expected_status": "FLAGGED",
        "expected_discrepancy_type": "AREA_MISMATCH",
        "expected_severity": "CRITICAL"
    },
    "survey_conflict": {
        "file_name": "survey_conflict_record_104_2.pdf",
        "doc_type": "CONVERSION_ORDER",
        "description": "Conflicting commercial classification on agricultural parcel 104/2.",
        "content": (
            b"%PDF-1.4 [SYNTHETIC SURVEY CONFLICT]\n"
            b"State: Madhya Pradesh | District: Bhopal | Tehsil: Huzur | Village: Bairagarh\n"
            b"Khasra No: 104/2 | Khata No: 45 | Area: 1.2500 ha | Type: Commercial\n"
            b"Owner: Ram Prasad Sharma\n"
        ),
        "expected_status": "FLAGGED",
        "expected_discrepancy_type": "SURVEY_CONFLICT",
        "expected_severity": "HIGH"
    },
    "low_confidence": {
        "file_name": "low_confidence_record_104_2.pdf",
        "doc_type": "JAMABANDI",
        "description": "Degraded OCR scan with low confidence (< 0.60) on mandatory fields.",
        "content": (
            b"%PDF-1.4 [SYNTHETIC DEGRADED SCAN WITH POOR OCR CONFIDENCE]\n"
            b"State: Madhya Pradesh | District: Bhopal | Tehsil: Huzur | Village: Bairagarh\n"
            b"Khasra No: 104/2 | Khata No: 45 | Area: 1.2500 ha\n"
        ),
        "expected_status": "FLAGGED",
        "expected_discrepancy_type": "LOW_CONFIDENCE_CRITICAL_FIELD",
        "expected_severity": "HIGH"
    },
    "duplicate_document": {
        "file_name": "duplicate_document_record_104_2.pdf",
        "doc_type": "JAMABANDI",
        "description": "Duplicate re-filing of identical attributes for parcel 104/2 under new submission.",
        "content": (
            b"%PDF-1.4 [SYNTHETIC DUPLICATE SUBMISSION]\n"
            b"State: Madhya Pradesh | District: Bhopal | Tehsil: Huzur | Village: Bairagarh\n"
            b"Khasra No: 104/2 | Khata No: 45 | Area: 1.2500 ha | Type: Agricultural\n"
            b"Owner: Ram Prasad Sharma | Co-owner: Shyam Prasad Sharma\n"
        ),
        "expected_status": "VALIDATED",
        "expected_discrepancy_type": "DUPLICATE_DOCUMENT",
        "expected_severity": "MEDIUM"
    },
    "corrupt_scan": {
        "file_name": "corrupt_unreadable_scan.pdf",
        "doc_type": "JAMABANDI",
        "description": "Severely corrupt file that fails OCR processing and halts pipeline gracefully.",
        "content": b"%PDF-1.4 [CORRUPT UNREADABLE BINARY NOISE]\x00\xff\xfe\xaa\xbb\xcc",
        "expected_error": "ExtractionProcessingError"
    }
}
