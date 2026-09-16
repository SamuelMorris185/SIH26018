from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.audit_log import AuditLogModel
from app.services.ai.schemas import (
    AIInterpretationResult,
    GeminiFieldSuggestion,
    GeminiLandRecordInterpretation,
)
from app.services.digitization_service import digitization_service
from app.services.extraction.provider import MockExtractionProvider


def process_document(client):
    response = client.post(
        "/api/v1/digitization/upload-and-process",
        files={"file": ("ai_test.pdf", b"%PDF-1.4 test", "application/pdf")},
        data={"doc_type": "JAMABANDI"},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.anyio
async def test_ai_merge_persists_conflicts_and_confidence(client, db_session, monkeypatch):
    class MissingPattaProvider(MockExtractionProvider):
        async def extract_document_fields(self, **kwargs):
            payload = await super().extract_document_fields(**kwargs)
            payload.extracted_fields.pop("patta_number", None)
            payload.structured_fields.pop("patta_number", None)
            payload.field_confidences.pop("patta_number", None)
            return payload

    monkeypatch.setattr(digitization_service, "_extraction_provider", MissingPattaProvider())
    provider = AsyncMock()
    provider.is_available = True
    provider.interpret_land_record.return_value = AIInterpretationResult(
        ai_used=True,
        status="SUCCESS",
        provider="TEST_AI",
        suggested_fields={"owner_name": "Conflicting Owner", "patta_number": "P-42"},
        interpretation=GeminiLandRecordInterpretation(
            patta_number=GeminiFieldSuggestion(value="P-42", confidence=0.4)
        ),
    )
    monkeypatch.setattr(digitization_service, "_ai_provider", provider)
    result = process_document(client)
    extraction = result["extraction"]
    assert result["records"][0]["owner_name"] != "Conflicting Owner"
    assert extraction["structured_fields"]["patta_number"]["source"] == "ai_assistant"
    assert extraction["field_confidences"]["patta_number"] == 0.4
    assert "patta_number" in extraction["low_confidence_fields"]
    conflicts = extraction["ai_metadata"]["conflicts"]
    assert any(conflict["field"] == "owner_name" for conflict in conflicts)
    event = (await db_session.execute(select(AuditLogModel).where(
        AuditLogModel.action == "AI_INTERPRETATION_COMPLETED"
    ))).scalar_one()
    assert event.new_state["conflicts_count"] == len(conflicts)


@pytest.mark.anyio
async def test_ai_exception_keeps_pipeline_available(client, db_session, monkeypatch):
    provider = AsyncMock()
    provider.is_available = True
    provider.interpret_land_record.side_effect = RuntimeError("private provider detail")
    monkeypatch.setattr(digitization_service, "_ai_provider", provider)
    result = process_document(client)
    assert result["extraction"]["ai_metadata"]["status"] == "FAILED"
    assert result["records"]
    event = (await db_session.execute(select(AuditLogModel).where(
        AuditLogModel.action == "AI_INTERPRETATION_FAILED"
    ))).scalar_one()
    assert "private provider detail" not in str(event.new_state)


def test_ai_missing_key_keeps_pipeline_available(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(digitization_service, "_ai_provider", None)
    result = process_document(client)
    assert result["records"]
    assert result["extraction"]["ai_metadata"] is None
