import io
import uuid
import pytest
from PIL import Image, ImageDraw
from app.core.config import settings
from app.core.exceptions import ExtractionProcessingError
from app.services.extraction.image_analysis import load_image,analyze_quality,correct_image
from app.services.extraction.authenticity import DocumentAuthenticityAnalyzer,risk_result
from app.services.extraction.consensus import consensus
from app.services.extraction.tesseract_provider import TesseractOCRProvider
from tests.fixtures.sample_documents.manifest import get_fixture_bytes


def test_quality_and_no_original_mutation():
    data=get_fixture_bytes('clean_land_record.png');image=load_image(data)
    original=image.tobytes();quality=analyze_quality(image);corrected,meta=correct_image(image,quality)
    assert quality['quality_score']>70
    assert quality['glare_score']==0  # white paper is not glare
    assert image.tobytes()==original
    assert corrected.mode=='L'


def test_severe_blur_recapture():
    quality=analyze_quality(load_image(get_fixture_bytes('noisy_land_record.png')))
    assert quality['recommended_action']=='RECAPTURE_RECOMMENDED'


def test_pixel_guard(monkeypatch):
    monkeypatch.setattr(settings,'OCR_MAX_PIXELS',10)
    with pytest.raises(ExtractionProcessingError): load_image(get_fixture_bytes('clean_land_record.png'))


def test_exif_orientation():
    image=Image.new('RGB',(80,140),'white');exif=Image.Exif();exif[274]=6
    out=io.BytesIO();image.save(out,format='JPEG',exif=exif)
    assert load_image(out.getvalue()).size==(140,80)


@pytest.mark.parametrize('jpeg',[False,True])
def test_missing_metadata_and_recompression_not_high(jpeg):
    image=load_image(get_fixture_bytes('clean_land_record.png'))
    buf=io.BytesIO();image.save(buf,format='JPEG' if jpeg else 'PNG',**({'quality':35} if jpeg else {}))
    risk=DocumentAuthenticityAnalyzer().analyze(image,buf.getvalue())
    assert risk['risk_level']!='HIGH'
    assert not risk['requires_manual_review']
    assert 'do not independently prove' in risk['disclaimer']


def test_risk_independent_signal_policy():
    signals=[dict(code='LOCAL_RESIDUAL',family='local_consistency',weight=20),dict(code='EDGE_SHARPNESS',family='local_consistency',weight=20)]
    assert risk_result(signals)['risk_level']=='MEDIUM'
    signals.append(dict(code='COPY_MOVE',family='copy_move',weight=40))
    result=risk_result(signals)
    assert result['risk_level']=='HIGH' and result['requires_manual_review']
    assert result['risk_score']==70


def test_consensus_literal_and_alternative():
    provider=TesseractOCRProvider();passes=[]
    for i,(value,score) in enumerate([('104/2',.93),('104/2',.89),('104/7',.48)]):
        evidence=provider._parse_land_record_text(f'Khasra: {value}',score)[2]
        passes.append(dict(id=str(i),page=1,evidence=evidence))
    fields,_,evidence,_=consensus(passes)
    assert fields['khasra_number']=='104/2'
    assert evidence['khasra_number'].supporting_passes==['0','1']
    assert evidence['khasra_number'].alternatives[0]['value']=='104/7'
    assert evidence['khasra_number'].requires_review
    assert fields['owner_name'] is None


def test_parser_no_invented_classification_or_partial_identifier():
    fields,_,_,_=TesseractOCRProvider()._parse_land_record_text('Co-owner: Jane Doe\nKhasra: 104/??/2',.95)
    assert fields['owner_name'] == ''
    assert fields['land_classification'] == ''
    assert fields['khasra_number']=='104/??/2'


@pytest.mark.parametrize('area,expected',[('2 acres',.8094),('10000 sq m',1.0)])
def test_area_units_preserved(area,expected):
    fields,_,evidence,_=TesseractOCRProvider()._parse_land_record_text(f'Area: {area}',.95)
    assert fields['area_in_hectares']==area
    assert evidence['area_in_hectares'].normalized_value==expected


def test_edited_and_copy_move_images_are_risk_not_legal_verdicts():
    image=load_image(get_fixture_bytes('clean_land_record.png'))
    edited=image.copy();draw=ImageDraw.Draw(edited);draw.rectangle((70,320,400,365),fill='white');draw.text((80,330),'Changed field',fill='black')
    copied=image.copy();copied.paste(image.crop((50,80,700,650)),(800,300))
    for candidate in (edited,copied):
        result=DocumentAuthenticityAnalyzer().analyze(candidate)
        assert result['risk_level'] in {'LOW','MEDIUM','HIGH'}
        assert 'Synthetic-image origin could not be conclusively determined.' in result['limitations']
        assert 'fake' not in result['disclaimer'].lower()
