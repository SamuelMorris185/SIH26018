from typing import Optional
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import OCREngineUnavailableError
from app.services.extraction.provider import BaseExtractionProvider, MockExtractionProvider
from app.services.extraction.tesseract_provider import TesseractOCRProvider

def get_extraction_provider(engine_name: Optional[str] = None) -> BaseExtractionProvider:
    """
    Factory resolving the active document extraction provider based on environment configuration.
    Supports MOCK (MOCK_OCR_V1) and TESSERACT (TESSERACT_OCR_V1).
    """
    selected = (engine_name or settings.OCR_ENGINE).strip().upper()
    
    if selected == "TESSERACT":
        logger.info("[OCR_FACTORY] Instantiating TesseractOCRProvider")
        return TesseractOCRProvider()
    elif selected == "MOCK":
        return MockExtractionProvider()
    else:
        raise OCREngineUnavailableError(selected, "Unknown OCR_ENGINE; use MOCK or TESSERACT.")
