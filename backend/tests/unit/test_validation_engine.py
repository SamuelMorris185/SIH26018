import uuid
import pytest
from app.services.validation.rules import (
    RequiredFieldsRule,
    AreaSanityRule,
    KhasraFormatRule,
    ConfidenceThresholdRule,
    LandClassificationRule,
)
from app.services.validation.engine import ValidationEngine

def test_required_fields_rule():
    rule = RequiredFieldsRule()
    valid_data = {
        "state": "Madhya Pradesh",
        "district": "Bhopal",
        "tehsil": "Huzur",
        "village": "Bairagarh",
        "khasra_number": "104/2",
        "khata_number": "45"
    }
    res = rule.evaluate(valid_data)
    assert res.passed is True

    missing_data = {
        "state": "Madhya Pradesh",
        "district": "Bhopal",
        "tehsil": "",
        "village": None
    }
    res2 = rule.evaluate(missing_data)
    assert res2.passed is False
    assert "Missing mandatory fields" in res2.message

def test_area_sanity_rule():
    rule = AreaSanityRule()
    assert rule.evaluate({"area_in_hectares": 1.25}).passed is True
    assert rule.evaluate({"area_in_hectares": 0.0001}).passed is True
    assert rule.evaluate({"area_in_hectares": 0}).passed is False
    assert rule.evaluate({"area_in_hectares": -5.0}).passed is False
    assert rule.evaluate({"area_in_hectares": 501.0}).passed is False
    assert rule.evaluate({"area_in_hectares": "not_a_number"}).passed is False

def test_khasra_format_rule():
    rule = KhasraFormatRule()
    assert rule.evaluate({"khasra_number": "104"}).passed is True
    assert rule.evaluate({"khasra_number": "104/2"}).passed is True
    assert rule.evaluate({"khasra_number": "104-A"}).passed is True
    assert rule.evaluate({"khasra_number": "104/2B"}).passed is True
    assert rule.evaluate({"khasra_number": ""}).passed is False
    assert rule.evaluate({"khasra_number": "&&INVALID##"}).passed is False

def test_confidence_threshold_rule():
    rule = ConfidenceThresholdRule()
    assert rule.evaluate({"confidence_score": 0.95}).passed is True
    assert rule.evaluate({"confidence_score": 0.70}).passed is True
    res = rule.evaluate({"confidence_score": 0.50})
    assert res.passed is False
    assert res.severity == "WARNING"

def test_land_classification_rule():
    rule = LandClassificationRule()
    assert rule.evaluate({"land_classification": "Agricultural"}).passed is True
    assert rule.evaluate({"land_classification": "Residential"}).passed is True
    assert rule.evaluate({"land_classification": "SpacePort"}).passed is False

def test_validation_engine_complete():
    engine = ValidationEngine()
    record_id = uuid.uuid4()

    valid_record = {
        "state": "Madhya Pradesh",
        "district": "Bhopal",
        "tehsil": "Huzur",
        "village": "Bairagarh",
        "khasra_number": "104/2",
        "khata_number": "45",
        "area_in_hectares": 1.25,
        "land_classification": "Agricultural",
        "confidence_score": 0.94
    }
    result = engine.evaluate_record(record_id, valid_record)
    assert result.is_valid is True
    assert result.status == "VALIDATED"
    assert len(result.rule_results) == 5

    flawed_record = {
        "state": "Madhya Pradesh",
        "district": "",
        "tehsil": "Huzur",
        "village": "Bairagarh",
        "khasra_number": "104/2",
        "khata_number": "45",
        "area_in_hectares": -1.0, # Error
        "land_classification": "UnknownType", # Warning
        "confidence_score": 0.40 # Warning
    }
    flawed_result = engine.evaluate_record(record_id, flawed_record)
    assert flawed_result.is_valid is False
    assert flawed_result.status == "FLAGGED"
    assert "AREA_SANITY_CHECK" in flawed_result.discrepancy_summary
