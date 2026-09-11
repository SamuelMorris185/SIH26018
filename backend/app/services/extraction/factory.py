from typing import Optional
from app.core.config import settings
from app.core.logging import logger
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
        logger.warning(f"[OCR_FACTORY] Unknown OCR engine '{selected}'. Falling back to MockExtractionProvider.")
        return MockExtractionProvider()
