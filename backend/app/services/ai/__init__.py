"""
SIH26018 Intelligent Land Record Digitization and Validation System
AI Intelligence Package
"""

from app.services.ai.schemas import (
    GeminiLandRecordInterpretation,
    GeminiFieldSuggestion,
    AIInterpretationResult,
    AIFieldConflict,
)
from app.services.ai.base import BaseAIProvider
from app.services.ai.gemini_provider import GeminiAIProvider
from app.services.ai.merge_service import AIMergeService
from app.services.ai.factory import get_ai_provider

__all__ = [
    "GeminiLandRecordInterpretation",
    "GeminiFieldSuggestion",
    "AIInterpretationResult",
    "AIFieldConflict",
    "BaseAIProvider",
    "GeminiAIProvider",
    "AIMergeService",
    "get_ai_provider",
]
