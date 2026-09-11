import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.core.logging import logger
from app.schemas.validation import RuleValidationResult, ValidationCheckResponse
from app.services.validation.rules import (
    BaseValidationRule,
    RequiredFieldsRule,
    AreaSanityRule,
    KhasraFormatRule,
    ConfidenceThresholdRule,
    LandClassificationRule,
)

class ValidationEngine:
    """
    Modular Rule Engine orchestrating verification checks across land record entities.
    Determines overall VALIDATED vs FLAGGED state and creates discrepancy reports.
    """

    def __init__(self, rules: Optional[List[BaseValidationRule]] = None):
        self.rules: List[BaseValidationRule] = rules or [
            RequiredFieldsRule(),
            AreaSanityRule(),
            KhasraFormatRule(),
            ConfidenceThresholdRule(),
            LandClassificationRule()
        ]

    def add_rule(self, rule: BaseValidationRule) -> None:
        self.rules.append(rule)

    def evaluate_record(self, record_id: uuid.UUID, record_data: Dict[str, Any]) -> ValidationCheckResponse:
        logger.info(f"Running validation engine ({len(self.rules)} rules) on record {record_id}")
        
        rule_results: List[RuleValidationResult] = []
        critical_failure = False
        discrepancies: List[str] = []

        for rule in self.rules:
            result = rule.evaluate(record_data)
            rule_results.append(result)

            if not result.passed:
                discrepancies.append(f"[{result.rule_name}]: {result.message}")
                if result.severity == "ERROR":
                    critical_failure = True

        # Overall validity: record is valid only if all ERROR-level rules passed
        is_valid = not critical_failure
        status = "VALIDATED" if is_valid else "FLAGGED"

        summary = "; ".join(discrepancies) if discrepancies else "Record passed all validation rules successfully."

        return ValidationCheckResponse(
            record_id=record_id,
            is_valid=is_valid,
            status=status,
            rule_results=rule_results,
            discrepancy_summary=summary,
            validated_at=datetime.now(timezone.utc)
        )
