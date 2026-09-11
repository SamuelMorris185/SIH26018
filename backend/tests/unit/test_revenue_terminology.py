import pytest
from app.services.extraction.tesseract_provider import TesseractOCRProvider
from app.schemas.extraction import ConfidenceCategory

def test_indian_revenue_terminology_variations():
    provider = TesseractOCRProvider()
    
    ocr_sample = (
        "GOVERNMENT REVENUE DEPARTMENT\n"
        "Rajya: Madhya Pradesh\n"
        "Jila: Bhopal\n"
        "Taluka: Huzur\n"
        "Mauza: Bairagarh\n"
        "Gat No: 104/2\n"
        "Khatauni: 45\n"
        "Rakba: 1.2500 ha\n"
        "Kism: Agricultural\n"
        "Khatedar: Ram Prasad Sharma\n"
        "Sah-Khatedar: Shyam Prasad Sharma\n"
        "Patta No: PATTA-2024-889\n"
        "Dastavej No: REG-2024-MP-00123\n"
        "Namantaran No: MUT-2024-00456\n"
        "Tarikh: 2024-01-15\n"
    )

    extracted, confidences, structured, low_conf = provider._parse_land_record_text(
        text=ocr_sample,
        base_confidence=0.92
    )

    # Verify field extraction from regional variations
    assert extracted["state"] == "Madhya Pradesh"
    assert extracted["district"] == "Bhopal"
    assert extracted["tehsil"] == "Huzur"
    assert extracted["village"] == "Bairagarh"
    assert extracted["khasra_number"] == "104/2"
    assert extracted["khata_number"] == "45"
    assert extracted["area_in_hectares"] == "1.2500 ha"
    assert extracted["land_classification"] == "Agricultural"
    assert extracted["owner_name"] == "Ram Prasad Sharma"
    assert extracted["co_owners"] == "Shyam Prasad Sharma"
    assert extracted["patta_number"] == "PATTA-2024-889"
    assert extracted["registration_number"] == "REG-2024-MP-00123"
    assert extracted["mutation_number"] == "MUT-2024-00456"
    assert extracted["document_date"] == "2024-01-15"

    # Verify dual preservation in structured_fields
    assert structured["khasra_number"].value == "104/2"
    assert structured["khasra_number"].normalized_value == "104/2"

    assert structured["area_in_hectares"].value == "1.2500 ha"
    assert structured["area_in_hectares"].normalized_value == 1.25

    assert structured["owner_name"].value == "Ram Prasad Sharma"
    assert structured["owner_name"].normalized_value == "Ram Prasad Sharma"

    assert structured["co_owners"].value == "Shyam Prasad Sharma"
    assert structured["co_owners"].normalized_value == ["Shyam Prasad Sharma"]

    assert structured["document_date"].normalized_value == "2024-01-15"

def test_survey_number_and_mandal_variations():
    provider = TesseractOCRProvider()
    
    ocr_sample = (
        "Prant: Andhra Pradesh\n"
        "Zilla: Visakhapatnam\n"
        "Mandal: Anandapuram\n"
        "Gram: Gambheeram\n"
        "Survey Number: 402/1\n"
        "Account No: 882\n"
        "Extent: 2.5000 ha\n"
        "Land Type: Non-Agricultural\n"
        "Name of Owner: Venkata Rao\n"
        "Joint Holders: Lakshmi Devi\n"
        "Reg No: REG-AP-2024-01\n"
        "Mutation No: MUT-AP-2024-02\n"
    )

    extracted, confidences, structured, low_conf = provider._parse_land_record_text(
        text=ocr_sample,
        base_confidence=0.90
    )

    assert extracted["state"] == "Andhra Pradesh"
    assert extracted["district"] == "Visakhapatnam"
    assert extracted["tehsil"] == "Anandapuram"
    assert extracted["village"] == "Gambheeram"
    assert extracted["khasra_number"] == "402/1"
    assert extracted["khata_number"] == "882"
    assert extracted["owner_name"] == "Venkata Rao"
    assert structured["land_classification"].normalized_value == "Non-Agricultural"
