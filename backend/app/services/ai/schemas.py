"""
SIH26018 Intelligent Land Record Digitization and Validation System
Pydantic Schemas for AI Land Record Interpretation & Structured Output
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class GeminiFieldSuggestion(BaseModel):
    """Represents an AI-suggested interpretation of a land record field."""
    value: Optional[str] = Field(default=None, description="Suggested normalized text or numerical string for the field")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Confidence assessment of this suggestion")
    evidence: Optional[str] = Field(default=None, description="Exact OCR text snippet supporting this interpretation")


class GeminiLandRecordInterpretation(BaseModel):
    """
    Strict structured output schema for Gemini 3.8 Flash interpretation.
    Covers Indian revenue terminology (Jamabandi, Patta, Mutation, Record of Rights).
    """
    state: Optional[GeminiFieldSuggestion] = Field(default=None, description="Indian State (e.g. Madhya Pradesh, Rajasthan)")
    district: Optional[GeminiFieldSuggestion] = Field(default=None, description="District name (e.g. Bhopal, Jaipur)")
    tehsil: Optional[GeminiFieldSuggestion] = Field(default=None, description="Tehsil or Taluk name (e.g. Huzur, Sanganer)")
    village: Optional[GeminiFieldSuggestion] = Field(default=None, description="Village or Mauza name (e.g. Bairagarh)")
    khasra_number: Optional[GeminiFieldSuggestion] = Field(default=None, description="Khasra or Survey plot number (e.g. 104/2)")
    khata_number: Optional[GeminiFieldSuggestion] = Field(default=None, description="Khata or Account number (e.g. 45)")
    area_in_hectares: Optional[GeminiFieldSuggestion] = Field(default=None, description="Land parcel area (e.g. 1.2500 ha)")
    area_unit: Optional[GeminiFieldSuggestion] = Field(default=None, description="Measurement unit (e.g. hectare, acre, sq m)")
    land_classification: Optional[GeminiFieldSuggestion] = Field(default=None, description="Land use type (e.g. Agricultural, Residential, Commercial)")
    owner_name: Optional[GeminiFieldSuggestion] = Field(default=None, description="Primary title holder name")
    co_owners: Optional[List[str]] = Field(default=None, description="List of co-owners or joint tenure holders")
    patta_number: Optional[GeminiFieldSuggestion] = Field(default=None, description="Patta allotment reference identifier")
    registration_number: Optional[GeminiFieldSuggestion] = Field(default=None, description="Official deed or registration number")
    mutation_number: Optional[GeminiFieldSuggestion] = Field(default=None, description="Mutation (Dakhil-Kharij) identifier")
    document_date: Optional[GeminiFieldSuggestion] = Field(default=None, description="Record creation or endorsement date (YYYY-MM-DD)")

    ambiguities: List[str] = Field(
        default_factory=list,
        description="Unclear, faded, or contradictory text segments observed in OCR"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Potential anomalies (e.g. unverified stamp, torn boundary, area mismatch)"
    )
    interpretation_summary: str = Field(
        default="",
        description="Brief concise summary of the interpretation without legal conclusions"
    )


class AIFieldConflict(BaseModel):
    """Represents a discrepancy between deterministic extraction and AI interpretation."""
    field: str
    deterministic_value: Any
    ai_value: Any
    resolution: str = "PRESERVED_DETERMINISTIC"
    severity: str = "WARNING"
    details: str = ""


class AIInterpretationResult(BaseModel):
    """
    Standard envelope wrapping AI interpretation for pipeline merging and audit persistence.
    """
    ai_used: bool = False
    provider: str = "none"
    model: str = ""
    interpretation: Optional[GeminiLandRecordInterpretation] = None
    suggested_fields: Dict[str, Any] = Field(default_factory=dict)
    conflicts: List[AIFieldConflict] = Field(default_factory=list)
    ambiguities: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    summary: str = ""
    status: str = "SKIPPED"  # SUCCESS, SKIPPED, FAILED
    error_message: Optional[str] = None
