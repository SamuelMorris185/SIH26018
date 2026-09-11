from abc import ABC, abstractmethod
import re
from typing import Dict, Any, List, Optional
from app.schemas.validation import RuleValidationResult

class BaseValidationRule(ABC):
    """Abstract base rule for land record verification."""

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Unique identifier for the rule."""
        pass

    @property
    def severity(self) -> str:
        """Severity when rule fails ('ERROR' or 'WARNING'). Defaults to 'ERROR'."""
        return "ERROR"

    @abstractmethod
    def evaluate(self, record_data: Dict[str, Any]) -> RuleValidationResult:
        """Executes verification check against record data."""
        pass

class RequiredFieldsRule(BaseValidationRule):
    """Verifies that all mandatory administrative and parcel fields are present and non-empty."""

    REQUIRED_FIELDS = ["state", "district", "tehsil", "village", "khasra_number", "khata_number"]

    @property
    def rule_name(self) -> str:
        return "REQUIRED_FIELDS_CHECK"

    def evaluate(self, record_data: Dict[str, Any]) -> RuleValidationResult:
        missing = [f for f in self.REQUIRED_FIELDS if not record_data.get(f)]
        if missing:
            return RuleValidationResult(
                rule_name=self.rule_name,
                passed=False,
                message=f"Missing mandatory fields: {', '.join(missing)}.",
                severity=self.severity
            )
        return RuleValidationResult(
            rule_name=self.rule_name,
            passed=True,
            message="All mandatory administrative fields are present.",
            severity=self.severity
        )

class AreaSanityRule(BaseValidationRule):
    """Verifies parcel area is positive, non-zero, and within realistic physical bounds."""

    MIN_AREA = 0.0001 # 1 sq. meter
    MAX_AREA = 500.0  # 500 hectares

    @property
    def rule_name(self) -> str:
        return "AREA_SANITY_CHECK"

    def evaluate(self, record_data: Dict[str, Any]) -> RuleValidationResult:
        area = record_data.get("area_in_hectares")
        if area is None:
            return RuleValidationResult(
                rule_name=self.rule_name,
                passed=False,
                message="Area value is missing.",
                severity=self.severity
            )
        try:
            val = float(area)
        except (ValueError, TypeError):
            return RuleValidationResult(
                rule_name=self.rule_name,
                passed=False,
                message=f"Invalid numeric area representation: {area}.",
                severity=self.severity
            )

        if val <= 0:
            return RuleValidationResult(
                rule_name=self.rule_name,
                passed=False,
                message=f"Area must be strictly greater than 0 (got {val}).",
                severity=self.severity
            )
        if val > self.MAX_AREA:
            return RuleValidationResult(
                rule_name=self.rule_name,
                passed=False,
                message=f"Area exceeds reasonable single parcel threshold of {self.MAX_AREA} hectares (got {val}).",
                severity=self.severity
            )

        return RuleValidationResult(
            rule_name=self.rule_name,
            passed=True,
            message="Area is within permissible bounds.",
            severity=self.severity
        )

class KhasraFormatRule(BaseValidationRule):
    """Validates khasra parcel number formatting (e.g. '104', '104/2', '104/2A', '104-A')."""

    # Matches numbers with optional letter suffix and optional sub-plot delimiter (e.g. 104, 104/2, 104-A, 104/2A)
    KHASRA_PATTERN = re.compile(r"^[0-9]+[A-Za-z]?([/\-]([0-9]+[A-Za-z]?|[A-Za-z]))?$")

    @property
    def rule_name(self) -> str:
        return "KHASRA_FORMAT_CHECK"

    def evaluate(self, record_data: Dict[str, Any]) -> RuleValidationResult:
        khasra = str(record_data.get("khasra_number") or "").strip()
        if not khasra:
            return RuleValidationResult(
                rule_name=self.rule_name,
                passed=False,
                message="Missing khasra identifier.",
                severity=self.severity
            )

        if not self.KHASRA_PATTERN.match(khasra):
            return RuleValidationResult(
                rule_name=self.rule_name,
                passed=False,
                message=f"Khasra '{khasra}' does not match standard parcel notation pattern.",
                severity="WARNING"
            )

        return RuleValidationResult(
            rule_name=self.rule_name,
            passed=True,
            message="Khasra format is valid.",
            severity=self.severity
        )

class ConfidenceThresholdRule(BaseValidationRule):
    """Verifies that the extraction confidence score meets the acceptable accuracy threshold."""

    THRESHOLD = 0.70

    @property
    def rule_name(self) -> str:
        return "CONFIDENCE_THRESHOLD_CHECK"

    @property
    def severity(self) -> str:
        return "WARNING"

    def evaluate(self, record_data: Dict[str, Any]) -> RuleValidationResult:
        score = record_data.get("confidence_score", 1.0)
        try:
            val = float(score)
        except (ValueError, TypeError):
            val = 1.0

        if val < self.THRESHOLD:
            return RuleValidationResult(
                rule_name=self.rule_name,
                passed=False,
                message=f"Extraction confidence score {val:.2f} is below threshold ({self.THRESHOLD:.2f}). Flagged for manual inspection.",
                severity=self.severity
            )

        return RuleValidationResult(
            rule_name=self.rule_name,
            passed=True,
            message=f"Confidence score {val:.2f} meets required threshold.",
            severity=self.severity
        )

class LandClassificationRule(BaseValidationRule):
    """Verifies that land classification matches recognized revenue categories."""

    ALLOWED_CLASSIFICATIONS = {
        "Agricultural", "Residential", "Commercial", "Industrial",
        "Forest", "Government", "Barren", "Non-Agricultural"
    }

    @property
    def rule_name(self) -> str:
        return "LAND_CLASSIFICATION_CHECK"

    def evaluate(self, record_data: Dict[str, Any]) -> RuleValidationResult:
        classification = record_data.get("land_classification")
        if not classification:
            return RuleValidationResult(
                rule_name=self.rule_name,
                passed=True,
                message="Classification not specified; defaulted to Agricultural.",
                severity=self.severity
            )

        if classification not in self.ALLOWED_CLASSIFICATIONS:
            return RuleValidationResult(
                rule_name=self.rule_name,
                passed=False,
                message=f"Unrecognized land classification: '{classification}'.",
                severity="WARNING"
            )

        return RuleValidationResult(
            rule_name=self.rule_name,
            passed=True,
            message=f"Valid land classification: '{classification}'.",
            severity=self.severity
        )
