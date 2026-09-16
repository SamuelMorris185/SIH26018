import pytest
from app.services.digitization_service import digitization_service
from app.services.extraction.provider import MockExtractionProvider
from app.services.extraction.tesseract_provider import TesseractOCRProvider
from app.services.extraction.authenticity import risk_result
from tests.fixtures.sample_documents.manifest import get_fixture_bytes


def test_high_risk_routes_to_review_never_rejects(client,monkeypatch):
    class HighRiskProvider(MockExtractionProvider):
        async def extract_document_fields(self,**kwargs):
            payload=await super().extract_document_fields(**kwargs)
            risk=risk_result([dict(code='COPY_MOVE',family='copy_move',weight=40),dict(code='LOCAL_RESIDUAL',family='local_consistency',weight=20)])
            payload.analysis=dict(version='test',pages=[dict(page=1,quality=None,authenticity=risk,preprocessing={})],
                                  requires_manual_review=True,review_reasons=['High authenticity risk requires human verification'])
            return payload
    monkeypatch.setattr(digitization_service,'_extraction_provider',HighRiskProvider())
    response=client.post('/api/v1/digitization/upload-and-process',files={'file':('risk.pdf',b'%PDF-1.4 test','application/pdf')})
    assert response.status_code==201,response.text
    result=response.json();record=result['records'][0]
    assert result['document']['status']=='FLAGGED'
    assert record['status']=='FLAGGED' and record['review_status']=='PENDING_REVIEW'
    assert record['owner_name']=='Ram Prasad Sharma'
    assert result['extraction']['analysis']['requires_manual_review']
    revalidate=client.post(f"/api/v1/records/{record['id']}/validate")
    assert revalidate.status_code==200,revalidate.text
    assert revalidate.json()['status']=='FLAGGED'


def test_real_ocr_analysis_persistence_preview_and_report(client,monkeypatch):
    monkeypatch.setattr(digitization_service,'_extraction_provider',TesseractOCRProvider())
    response=client.post('/api/v1/digitization/upload-and-process',files={'file':('analysis.png',get_fixture_bytes('clean_land_record.png'),'image/png')})
    assert response.status_code==201,response.text
    result=response.json();record=result['records'][0];doc=result['document']['id']
    assert record['khasra_number']=='104/2'
    assert result['extraction']['analysis']['pages'][0]['quality']['quality_score']>70
    assert result['extraction']['structured_fields']['owner_name']['supporting_passes']
    preview=client.get(f'/api/v1/documents/{doc}/analysis-preview')
    assert preview.status_code==200,preview.text
    assert preview.content.startswith(b'\x89PNG')
    assert client.get(f'/api/v1/documents/{doc}/content').content==get_fixture_bytes('clean_land_record.png')
    report=client.get(f"/api/v1/records/{record['id']}/verification-report")
    assert report.status_code==200,report.text
    import io,pypdf
    text=' '.join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(report.content)).pages)
    assert 'Authenticity risk' in text
    assert 'does not independently establish legal authenticity' in text
