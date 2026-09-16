"""
SIH26018 Intelligent Land Record Digitization and Validation System
Conservative Merge Policy Service (Deterministic Core vs. AI Assistance)
"""

from typing import Dict, Any, Tuple, Optional
from app.core.logging import logger
from app.core.config import settings
from app.schemas.extraction import (
    FieldExtractionEvidence,
    ConfidenceCategory,
    categorize_confidence,
)
from app.services.ai.schemas import (
    AIInterpretationResult,
    AIFieldConflict,
)


class AIMergeService:
    """
    Implements a strict, conservative merge policy between deterministic OCR extraction
    and optional AI interpretation suggestions.

    Governance Rules:
    1. Deterministic High-Confidence: If deterministic extraction has a valid value, KEEP IT.
       Gemini NEVER overwrites an existing high-confidence deterministic value.
    2. Augmentation of Missing Fields: If deterministic value is missing/empty/null and Gemini
       provides a valid interpretation, accept the suggestion and mark source as 'ai_assistant'.
    3. Conflict Recording: If deterministic and AI values differ, preserve the deterministic
       value and record an explicit AIFieldConflict for human reviewer visibility.
    4. Provenance: Every field in structured_fields retains explicit source ('ocr' vs 'ai_assistant').
    5. Authority: Downstream deterministic validation and cross-record discrepancy engines
       remain exclusively authoritative.
    """

    @staticmethod
    def _is_empty_value(val: Any) -> bool:
        if val is None:
            return True
        if isinstance(val, str) and not val.strip():
            return True
        if isinstance(val, (list, dict)) and len(val) == 0:
            return True
        return False

    @classmethod
    def merge(
        cls,
        deterministic_fields: Dict[str, Any],
        field_evidences: Optional[Dict[str, FieldExtractionEvidence]],
        ai_result: AIInterpretationResult
    ) -> Tuple[Dict[str, Any], Dict[str, FieldExtractionEvidence], AIInterpretationResult]:
        """
        Merges deterministic fields with AI interpretation according to conservative rules.
        Returns:
            merged_fields: Dict[str, Any] for normalization
            merged_evidences: Dict[str, FieldExtractionEvidence] for persistence
            updated_ai_result: AIInterpretationResult containing recorded conflicts
        """
        merged_fields = dict(deterministic_fields)
        merged_evidences = dict(field_evidences or {})

        if not ai_result.ai_used or not ai_result.suggested_fields:
            return merged_fields, merged_evidences, ai_result

        conflicts = list(ai_result.conflicts)
        suggested = ai_result.suggested_fields

        for field_name, ai_val in suggested.items():
            if cls._is_empty_value(ai_val):
                continue

            det_val = merged_fields.get(field_name)
            det_evidence = merged_evidences.get(field_name)

            # Rule A: Deterministic value exists
            if not cls._is_empty_value(det_val):
                det_str = str(det_val).strip().lower()
                ai_str = str(ai_val).strip().lower()

                # Check if values match
                if det_str == ai_str:
                    # Agreement between OCR and AI boosts confidence evidence
                    if det_evidence and det_evidence.confidence < 0.95:
                        det_evidence.confidence = min(1.0, det_evidence.confidence + 0.05)
                        det_evidence.category = categorize_confidence(det_evidence.confidence)
                else:
                    # Rule C: Conflict between deterministic and AI
                    # Deterministic ALWAYS wins; record the conflict for reviewer inspection
                    conflict = AIFieldConflict(
                        field=field_name,
                        deterministic_value=det_val,
                        ai_value=ai_val,
                        resolution="PRESERVED_DETERMINISTIC",
                        severity="WARNING",
                        details=(
                            f"Deterministic OCR extracted '{det_val}', while AI suggested '{ai_val}'. "
                            "Deterministic value preserved per conservative safety policy."
                        )
                    )
                    conflicts.append(conflict)
                    logger.info(
                        f"[AI_MERGE] Conflict recorded on '{field_name}': "
                        f"deterministic='{det_val}' vs ai='{ai_val}' (deterministic preserved)"
                    )
            else:
                # Rule B: Deterministic value missing/empty; accept AI suggestion
                merged_fields[field_name] = ai_val

                # Get confidence from AI interpretation if available
                field_conf = 0.80
                evidence_text = "AI-assisted interpretation from raw OCR text"
                if ai_result.interpretation:
                    sugg_obj = getattr(ai_result.interpretation, field_name, None)
                    if sugg_obj and hasattr(sugg_obj, "confidence"):
                        field_conf = float(sugg_obj.confidence)
                    if sugg_obj and hasattr(sugg_obj, "evidence") and sugg_obj.evidence:
                        evidence_text = f"AI evidence: {sugg_obj.evidence}"

                # Rule D: Explicitly tag source as 'ai_assistant'
                merged_evidences[field_name] = FieldExtractionEvidence(
                    field=field_name,
                    value=ai_val,
                    normalized_value=ai_val,
                    confidence=field_conf,
                    category=categorize_confidence(field_conf),
                    source="ai_assistant",
                    evidence=evidence_text
                )
                logger.info(f"[AI_MERGE] Augmented missing field '{field_name}' with AI suggestion: '{ai_val}'")

        # Update AI result envelope with recorded conflicts
        ai_result.conflicts = conflicts
        return merged_fields, merged_evidences, ai_result
