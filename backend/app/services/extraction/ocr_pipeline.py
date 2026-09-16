"""Bounded per-page OCR with quality, corrections, literal consensus and forensic triage."""
import io
import time
import re
import numpy as np
from PIL import Image
import pytesseract
from app.core.config import settings
from app.core.exceptions import ExtractionProcessingError
from app.schemas.extraction import RawExtractionPayload, categorize_confidence
from .image_analysis import load_image, analyze_quality, correct_image, variants
from .authenticity import DocumentAuthenticityAnalyzer, risk_result
from .consensus import consensus, CRITICAL_FIELDS


def image_pages(data, is_pdf):
    if not is_pdf:
        # TIFF pages are independently decoded and numbered; original bytes remain untouched.
        with Image.open(io.BytesIO(data)) as source:
            count = getattr(source,'n_frames',1)
            if count > settings.OCR_MAX_PAGES: raise ExtractionProcessingError('Too many image pages.')
            for n in range(count):
                source.seek(n)
                if source.width*source.height > settings.OCR_MAX_PIXELS: raise ExtractionProcessingError('Image exceeds pixel limit.')
                if count == 1: yield n+1, load_image(data), None
                else:
                    buffer=io.BytesIO(); source.save(buffer,format='PNG')
                    yield n+1,load_image(buffer.getvalue()),None
        return
    import pypdf
    import pypdfium2 as pdfium
    reader=pypdf.PdfReader(io.BytesIO(data))
    if reader.is_encrypted: raise ExtractionProcessingError('Encrypted PDFs are unsupported. Upload an unlocked copy.')
    if len(reader.pages)>settings.OCR_MAX_PAGES: raise ExtractionProcessingError('PDF exceeds page limit.')
    renderer=None
    try:
        for n,page in enumerate(reader.pages):
            if len(page.get_contents().get_data()) > 8_000_000 if page.get_contents() else False:
                raise ExtractionProcessingError('PDF content stream exceeds analysis limit.')
            text=page.extract_text() or ''
            if len(text.strip())>40:
                yield n+1,None,text
            else:
                if renderer is None: renderer=pdfium.PdfDocument(data)
                rendered=renderer[n]
                try:
                    w,h=rendered.get_size()
                    scale=min(2.5,2400/max(w,h))
                    if w*h*scale*scale>settings.OCR_MAX_PIXELS: raise ExtractionProcessingError('PDF page exceeds pixel limit.')
                    bitmap=rendered.render(scale=scale)
                    try: image=bitmap.to_pil().convert('RGB')
                    finally: bitmap.close()
                    yield n+1,image,None
                finally: rendered.close()
    finally:
        if renderer: renderer.close()


def read_pass(provider, image, name, psm, languages, page, timeout):
    data=pytesseract.image_to_data(image,lang=languages,config=f'--oem 3 --psm {psm}',
                                   output_type=pytesseract.Output.DICT,timeout=timeout)
    lines={}
    for i,word in enumerate(data['text']):
        if not word.strip(): continue
        key=tuple(data[k][i] for k in ('block_num','par_num','line_num'))
        lines.setdefault(key,[]).append((word,max(0,float(data['conf'][i]))/100))
    text='\n'.join(' '.join(w for w,_ in words) for words in lines.values())
    confidences=[c for words in lines.values() for _,c in words]
    avg=sum(confidences)/len(confidences) if confidences else 0
    fields,scores,evidence,_=provider._parse_land_record_text(text,avg)
    for field,e in evidence.items():
        if not e.value: continue
        matched=[]
        for words in lines.values():
            line=' '.join(w for w,_ in words)
            if e.evidence and e.evidence.strip() in line:
                # Value words only, not the label or page mean.
                value_words=str(e.value).split()
                for start in range(len(words)):
                    if [w for w,_ in words[start:start+len(value_words)]] == value_words:
                        matched.extend(c for _,c in words[start:start+len(value_words)])
        if matched: e.confidence=min(e.confidence / .98,round(sum(matched)/len(matched),3)) if e.confidence < .5 else round(sum(matched)/len(matched),3)
        else: e.confidence=min(e.confidence,.59)
        if field=='khasra_number':
            from app.services.validation.rules import KhasraFormatRule
            if not KhasraFormatRule.KHASRA_PATTERN.fullmatch(str(e.normalized_value or '')): e.confidence=min(e.confidence,.49)
        if field=='area_in_hectares' and not re.search(r'\b(ha|hectares?|acres?|sq\.?\s*m|square\s*met)',str(e.value),re.I):
            e.confidence=min(e.confidence,.49); e.normalized_value=None
        scores[field]=e.confidence
    return dict(id=f'p{page}:{name}:psm{psm}',page=page,text=text,confidence=avg,evidence=evidence,source='tesseract_ocr')


def extract(provider,document_id,file_bytes,file_name,mime_type):
    started=time.monotonic(); deadline=started+settings.OCR_DOCUMENT_TIMEOUT_SECONDS
    if not file_bytes: raise ExtractionProcessingError('Cannot extract an empty document.')
    if len(file_bytes)>settings.MAX_UPLOAD_SIZE_BYTES: raise ExtractionProcessingError('Document exceeds upload limit.')
    available=provider.get_engine_status().get('supported_languages',[])
    languages=[x for x in settings.OCR_LANGUAGES.split('+') if x in available and x!='osd']
    if not languages: raise ExtractionProcessingError('No configured OCR language is installed.')
    passes=[]; pages=[]; texts=[]
    is_pdf=mime_type=='application/pdf' or file_name.lower().endswith('.pdf')
    def remaining():
        seconds=deadline-time.monotonic()
        if seconds<1: raise ExtractionProcessingError('Document analysis timed out. Split the document into fewer pages.')
        return min(settings.OCR_TIMEOUT_SECONDS,seconds)
    try:
        for number,image,digital_text in image_pages(file_bytes,is_pdf):
            remaining()
            if digital_text is not None:
                _,_,evidence,_=provider._parse_land_record_text(digital_text,.95)
                passes.append(dict(id=f'p{number}:digital',page=number,text=digital_text,confidence=.95,evidence=evidence,source='PDF_TEXT'))
                pages.append(dict(page=number,input_type='digital_pdf',quality=None,preprocessing={'operations':[]},
                                  authenticity={**risk_result([],['Digital PDF text was read directly; pixel forensics not performed.']), 'assessed':False}))
                texts.append(digital_text)
                continue
            quality=analyze_quality(image)
            gray,correction=correct_image(image,quality)
            correction['orientation_degrees']=0
            if 'osd' in available:
                try:
                    osd=pytesseract.image_to_osd(gray,output_type=pytesseract.Output.DICT,timeout=min(8,remaining()))
                    rotation=int(osd.get('rotate',0))
                    if rotation in (90,180,270) and float(osd.get('orientation_conf',0))>=2:
                        gray=gray.rotate(-rotation,expand=True,fillcolor=255)
                        correction['orientation_degrees']=rotation
                        correction['operations'].append('orientation_corrected')
                except RuntimeError: pass
            local=[]
            for name,variant,psm in list(variants(gray,quality))[:settings.OCR_MAX_PASSES]:
                item=read_pass(provider,variant,name,psm,'+'.join(languages),number,remaining())
                local.append(item)
                strong=all(item['evidence'][f].confidence>=.85 and item['evidence'][f].value for f in CRITICAL_FIELDS)
                if strong and quality['recommended_action']=='ACCEPT': break
                # Two agreeing strong passes are enough. Additional variants are correlated evidence.
                if len(local)>=2:
                    _,scores,evidence,_=consensus(local)
                    if all(scores[f]>=.85 and not evidence[f].requires_review for f in CRITICAL_FIELDS): break
            passes.extend(local)
            best=max(local,key=lambda x:x['confidence']); texts.append(best['text'])
            forensic=DocumentAuthenticityAnalyzer().analyze(image,None if is_pdf else file_bytes)
            pages.append(dict(page=number,input_type='raster_pdf' if is_pdf else 'image',quality=quality,
                              preprocessing=correction,authenticity=forensic))
    except ExtractionProcessingError: raise
    except Exception as exc:
        raise ExtractionProcessingError('Corrupt, unreadable or unsupported document; analysis could not complete safely.') from exc
    if not passes: raise ExtractionProcessingError('No readable pages found.')
    fields,scores,evidence,low=consensus(passes)
    # Keep unsupported/uncertain units from silently becoming hectares.
    area=evidence['area_in_hectares']
    fields['area_unit']='acre' if 'acre' in str(area.value).lower() else 'hectare' if re.search(r'\bha|hectare',str(area.value),re.I) else 'sq m' if re.search(r'sq\.?\s*m|square\s*met',str(area.value),re.I) else None
    if area.value and (fields['area_unit'] is None or area.normalized_value is None):
        scores['area_in_hectares']=area.confidence=min(area.confidence,.49)
        area.requires_review=True; area.category=categorize_confidence(area.confidence)
    review_fields=[f for f in CRITICAL_FIELDS if evidence[f].requires_review]
    review_reasons=[f'Needs verification: {f}' for f in review_fields]
    if any(p.get('quality') and p['quality']['recommended_action']=='RECAPTURE_RECOMMENDED' for p in pages): review_reasons.append('Recapture recommended by quality analysis.')
    if any(p['authenticity']['requires_manual_review'] for p in pages): review_reasons.append('High authenticity risk: human verification required; not a legal determination.')
    overall=round(sum(scores[f] for f in CRITICAL_FIELDS)/len(CRITICAL_FIELDS),3)
    analysis=dict(version='1.0',pages=pages,languages=languages,missing_languages=[x for x in settings.OCR_LANGUAGES.split('+') if x not in available],
                  passes=[{k:p[k] for k in ('id','page','confidence')} for p in passes],
                  requires_manual_review=bool(review_reasons),review_reasons=review_reasons,
                  elapsed_seconds=round(time.monotonic()-started,3),
                  limitations=['OCR confidence is a heuristic, not a calibrated accuracy probability.','Variants of the same image are correlated.',
                               'Multiple parcels in one document require manual separation; conflicting page values are flagged.'])
    return RawExtractionPayload(document_id=document_id,provider=provider.provider_name,raw_text='\n\f\n'.join(texts),
                                extracted_fields=fields,field_confidences=scores,structured_fields=evidence,
                                confidence_score=overall,confidence_category=categorize_confidence(overall),
                                low_confidence_fields=low,analysis=analysis)
