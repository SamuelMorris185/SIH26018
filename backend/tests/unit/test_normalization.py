import pytest
from app.services.normalization_service import NormalizationService

def test_clean_text():
    assert NormalizationService.clean_text("  Madhya    Pradesh  ") == "Madhya Pradesh"
    assert NormalizationService.clean_text(None) == ""
    assert NormalizationService.clean_text("\n\t  Bhopal \t ") == "Bhopal"

def test_normalize_title():
    assert NormalizationService.normalize_title("bhopal") == "Bhopal"
    assert NormalizationService.normalize_title("MADHYA PRADESH") == "Madhya Pradesh"
    assert NormalizationService.normalize_title("  huzur   tehsil ") == "Huzur Tehsil"

def test_normalize_khasra():
    assert NormalizationService.normalize_khasra(" 104 / 2 ") == "104/2"
    assert NormalizationService.normalize_khasra("  104 - A  ") == "104-A"
    assert NormalizationService.normalize_khasra("250/1/A") == "250/1/A"
    assert NormalizationService.normalize_khasra("") == ""

def test_normalize_khata():
    assert NormalizationService.normalize_khata("045") == "45"
    assert NormalizationService.normalize_khata("  00102  ") == "102"
    assert NormalizationService.normalize_khata("KH-12") == "KH-12"

def test_normalize_area():
    assert NormalizationService.normalize_area("1.2500 ha") == 1.25
    assert NormalizationService.normalize_area("2.5 Hectares") == 2.5
    assert NormalizationService.normalize_area(3.14159) == 3.1416
    assert NormalizationService.normalize_area("invalid") == 0.0
    assert NormalizationService.normalize_area(None) == 0.0

def test_normalize_classification():
    assert NormalizationService.normalize_classification("agri") == "Agricultural"
    assert NormalizationService.normalize_classification("krishi") == "Agricultural"
    assert NormalizationService.normalize_classification("residential") == "Residential"
    assert NormalizationService.normalize_classification("sarkari") == "Government"
    assert NormalizationService.normalize_classification("unknown_type") == "Unknown_type"

def test_deterministic_record_normalization():
    raw = {
        "state": "  madhya pradesh ",
        "district": "BHOPAL",
        "tehsil": " huzur ",
        "village": " bairagarh ",
        "khasra_number": "  104 / 2  ",
        "khata_number": "0045",
        "area_in_hectares": "1.2500 Hectares",
        "land_classification": "agri"
    }
    normalized = NormalizationService.normalize_record_data(raw)
    assert normalized == {
        "state": "Madhya Pradesh",
        "district": "Bhopal",
        "tehsil": "Huzur",
        "village": "Bairagarh",
        "khasra_number": "104/2",
        "khata_number": "45",
        "area_in_hectares": 1.25,
        "land_classification": "Agricultural"
    }
