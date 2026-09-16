"""
SIH26018 Intelligent Land Record Digitization and Validation System
Abstract Base Class for AI Interpretation Providers
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.services.ai.schemas import AIInterpretationResult


class BaseAIProvider(ABC):
    """
    Contract for optional AI interpretation providers (e.g. Gemini 3.8 Flash).
    AI providers serve strictly as assistants, not authorities.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the canonical provider name."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Returns the configured model identifier."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Returns whether the provider is configured and available."""
        pass

    @abstractmethod
    async def interpret_land_record(
        self,
        raw_text: str,
        deterministic_fields: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> AIInterpretationResult:
        """
        Interprets OCR raw text and deterministic fields to produce typed suggestions,
        identifying ambiguities and warnings without making authoritative legal determinations.
        """
        pass
