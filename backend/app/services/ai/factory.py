"""
SIH26018 Intelligent Land Record Digitization and Validation System
AI Provider Factory
"""

from typing import Optional
from app.core.config import settings
from app.core.logging import logger
from app.services.ai.base import BaseAIProvider
from app.services.ai.gemini_provider import GeminiAIProvider


def get_ai_provider(provider_name: Optional[str] = None) -> Optional[BaseAIProvider]:
    """
    Factory resolving the active AI interpretation provider.
    Returns None if AI_ENABLED is False or no provider is configured.
    """
    if not settings.AI_ENABLED:
        return None

    name = (provider_name or settings.AI_PROVIDER).strip().lower()

    if name in {"gemini", "google", "google-genai"}:
        return GeminiAIProvider()
    else:
        logger.warning(f"[AI_FACTORY] Unknown or unsupported AI provider '{name}'. AI assistance disabled.")
        return None
