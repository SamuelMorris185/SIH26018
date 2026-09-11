import pytest
from app.schemas.extraction import categorize_confidence, ConfidenceCategory

def test_confidence_boundary_thresholds():
    high_th = 0.85
    med_th = 0.60

    # 1. Exactly High threshold
    assert categorize_confidence(0.85, high_th, med_th) == ConfidenceCategory.HIGH

    # 2. Just above High threshold
    assert categorize_confidence(0.85001, high_th, med_th) == ConfidenceCategory.HIGH

    # 3. Just below High threshold
    assert categorize_confidence(0.84999, high_th, med_th) == ConfidenceCategory.MEDIUM

    # 4. Exactly Medium threshold
    assert categorize_confidence(0.60, high_th, med_th) == ConfidenceCategory.MEDIUM

    # 5. Just below Medium threshold
    assert categorize_confidence(0.59999, high_th, med_th) == ConfidenceCategory.LOW

    # 6. Absolute Zero
    assert categorize_confidence(0.0, high_th, med_th) == ConfidenceCategory.LOW

    # 7. Absolute One
    assert categorize_confidence(1.0, high_th, med_th) == ConfidenceCategory.HIGH

    # 8. Out of range underflow (< 0) bounded safely to 0.0 -> LOW
    assert categorize_confidence(-0.5, high_th, med_th) == ConfidenceCategory.LOW

    # 9. Out of range overflow (> 1.0) bounded safely to 1.0 -> HIGH
    assert categorize_confidence(1.75, high_th, med_th) == ConfidenceCategory.HIGH
