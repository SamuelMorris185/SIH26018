import re
import math
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.core.logging import logger

class NormalizationService:
    """
    Deterministic normalization service bridging raw extraction data and canonical land records.
    Applies non-destructive cleaning and canonicalization rules.
    """

    CLASSIFICATION_MAPPING = {
        "agricultural": "Agricultural",
        "agriculture": "Agricultural",
        "agri": "Agricultural",
        "krishi": "Agricultural",
        "residential": "Residential",
        "residence": "Residential",
        "commercial": "Commercial",
        "industrial": "Industrial",
        "forest": "Forest",
        "jangal": "Forest",
        "government": "Government",
        "govt": "Government",
        "sarkari": "Government",
        "barren": "Barren",
        "non-agricultural": "Non-Agricultural",
        "na": "Non-Agricultural"
    }

    @staticmethod
    def clean_text(value: Optional[str]) -> str:
        """Strips leading/trailing whitespace and collapses multiple internal spaces."""
        if not value:
            return ""
        return " ".join(str(value).strip().split())

    @staticmethod
    def normalize_title(value: Optional[str]) -> str:
        """Normalizes geographic names into title-cased canonical form."""
        cleaned = NormalizationService.clean_text(value)
        return cleaned.title() if cleaned else ""

    @staticmethod
    def normalize_name(value: Optional[str]) -> Optional[str]:
        """Normalizes human owner names, collapsing spaces and canonicalizing casing."""
        cleaned = NormalizationService.clean_text(value)
        if not cleaned:
            return None
        # Remove common honorific prefixes
        cleaned = re.sub(r"^(Shri|Smt\.?|Mr\.?|Mrs\.?|Ms\.?|Dr\.?)\s+", "", cleaned, flags=re.IGNORECASE)
        return cleaned.title()

    @staticmethod
    def normalize_co_owners(value: Any) -> Optional[List[str]]:
        """Normalizes co-owner lists from either arrays or comma-delimited strings."""
        if not value:
            return None
        names: List[str] = []
        if isinstance(value, list):
            for item in value:
                norm = NormalizationService.normalize_name(str(item))
                if norm:
                    names.append(norm)
        elif isinstance(value, str):
            for part in value.split(","):
                norm = NormalizationService.normalize_name(part)
                if norm:
                    names.append(norm)
        return names if names else None

    @staticmethod
    def normalize_identifier(value: Optional[str]) -> Optional[str]:
        """Normalizes legal registration, patta, or mutation identifiers."""
        cleaned = NormalizationService.clean_text(value)
        return cleaned.upper() if cleaned else None

    @staticmethod
    def normalize_date(value: Any) -> Optional[datetime]:
        """Safely parses common date formats into Python datetime objects."""
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        date_str = NormalizationService.clean_text(str(value))
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d.%m.%Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def normalize_khasra(value: Optional[str]) -> str:
        """Normalizes khasra parcel identifier (e.g. ' 104 / 2 ' -> '104/2')."""
        cleaned = NormalizationService.clean_text(value)
        # Remove spaces around slashes or hyphens
        cleaned = re.sub(r"\s*/\s*", "/", cleaned)
        cleaned = re.sub(r"\s*-\s*", "-", cleaned)
        return cleaned

    @staticmethod
    def normalize_khata(value: Optional[str]) -> str:
        """Normalizes khata account identifier."""
        cleaned = NormalizationService.clean_text(value)
        # Strip leading zeros if purely numeric (e.g. '045' -> '45')
        if cleaned.isdigit():
            return str(int(cleaned))
        return cleaned

    @staticmethod
    def normalize_area(value: Any) -> float:
        """
        Parses numeric area in hectares safely, stripping known unit markers ('ha', 'hectare', etc.).
        Returns float rounded to 4 decimal places. Defaults to 0.0 if unparseable.
        """
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return round(float(value), 4) if math.isfinite(value) else 0.0
        
        # If string, extract numeric component
        text = str(value).lower().strip()
        # Bigha varies by region; never silently treat it as hectares.
        if "bigha" in text:
            return 0.0
        factor = 0.40468564224 if "acre" in text else (0.0001 if re.search(r"sq\.?\s*m|m²|square\s*met", text) else 1.0)
        text = text.replace(",", "")
        match = re.search(r"[-+]?\d*\.?\d+", text)
        if match:
            try:
                parsed = float(match.group(0))
                return round(parsed * factor, 4)
            except ValueError:
                return 0.0
        return 0.0

    @staticmethod
    def normalize_classification(value: Optional[str]) -> str:
        """Maps diverse land classification labels to canonical categories."""
        cleaned = NormalizationService.clean_text(value).lower()
        if not cleaned:
            return "Agricultural"
        return NormalizationService.CLASSIFICATION_MAPPING.get(cleaned, cleaned.capitalize())

    @classmethod
    def normalize_record_data(cls, raw_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforms raw extracted field dictionary into canonical normalized land record payload.
        """
        logger.debug(f"Normalizing raw extraction fields: {raw_fields}")

        normalized: Dict[str, Any] = {
            "state": cls.normalize_title(raw_fields.get("state")),
            "district": cls.normalize_title(raw_fields.get("district")),
            "tehsil": cls.normalize_title(raw_fields.get("tehsil")),
            "village": cls.normalize_title(raw_fields.get("village")),
            "khasra_number": cls.normalize_khasra(raw_fields.get("khasra_number")),
            "khata_number": cls.normalize_khata(raw_fields.get("khata_number")),
            "area_in_hectares": cls.normalize_area(raw_fields.get("area_in_hectares")),
            "land_classification": cls.normalize_classification(raw_fields.get("land_classification"))
        }

        # Phase 5: Structured Ownership & Legal Metadata (populated when provided)
        if "owner_name" in raw_fields:
            normalized["owner_name"] = cls.normalize_name(raw_fields.get("owner_name"))
        if "co_owners" in raw_fields:
            normalized["co_owners"] = cls.normalize_co_owners(raw_fields.get("co_owners"))
        if "patta_number" in raw_fields:
            normalized["patta_number"] = cls.normalize_identifier(raw_fields.get("patta_number"))
        if "registration_number" in raw_fields:
            normalized["registration_number"] = cls.normalize_identifier(raw_fields.get("registration_number"))
        if "mutation_number" in raw_fields:
            normalized["mutation_number"] = cls.normalize_identifier(raw_fields.get("mutation_number"))
        if "document_date" in raw_fields:
            normalized["document_date"] = cls.normalize_date(raw_fields.get("document_date"))

        logger.debug(f"Normalized land record result: {normalized}")
        return normalized
