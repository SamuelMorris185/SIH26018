"""Fixture-only benchmark. Never writes to canonical fixtures or the application database.

Run with --baseline-provider <snapshot.py> to compare the pre-change provider captured
before implementation. Expectations come exclusively from the checked-in fixture manifest.
"""
import argparse
import asyncio
import importlib.util
import io
import json
import sys
import time
import uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from PIL import Image,ImageEnhance,ImageFilter
from app.services.extraction.tesseract_provider import TesseractOCRProvider
from app.services.normalization_service import NormalizationService
from tests.fixtures.sample_documents.manifest import REAL_OCR_FIXTURES, get_fixture_bytes


def degraded_images():
    image=Image.open(io.BytesIO(get_fixture_bytes('clean_land_record.png'))).convert('RGB')
    w,h=image.size
    source=np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]])
    target=np.float32([[120,100],[w-110,30],[w-30,h-70],[40,h-20]])
    perspective=Image.fromarray(cv2.warpPerspective(np.asarray(image),cv2.getPerspectiveTransform(source,target),(w,h),borderValue=(50,50,50)))
    rng=np.random.default_rng(42)
    noise=Image.fromarray(np.clip(np.asarray(image).astype(float)+rng.normal(0,6,(h,w,3)),0,255).astype('uint8'))
    cases={'clean':image,'rotation':image.rotate(5,expand=True,fillcolor='white'), 'perspective':perspective,
           'blur':image.filter(ImageFilter.GaussianBlur(1)), 'dark':ImageEnhance.Brightness(image).enhance(.45),
           'bright':ImageEnhance.Brightness(image).enhance(1.5),'contrast':ImageEnhance.Contrast(image).enhance(.3),
           'noise':noise,'jpeg':image,'rotation90':image.rotate(90,expand=True),'rotation180':image.rotate(180,expand=True)}
    for name,img in cases.items():
        buffer=io.BytesIO();img.save(buffer,format='JPEG' if name=='jpeg' else 'PNG',**({'quality':45} if name=='jpeg' else {}))
        yield name,buffer.getvalue()


async def run(args):
    providers={'after':TesseractOCRProvider()}
    if args.baseline_provider:
        spec=importlib.util.spec_from_file_location('baseline_ocr',args.baseline_provider)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        providers={'before':module.TesseractOCRProvider(),**providers}
    truth=REAL_OCR_FIXTURES['clean_record_image']['expected_fields']
    results=[]
    for name,data in degraded_images():
        for version,provider in providers.items():
            start=time.perf_counter()
            result=await provider.extract_document_fields(uuid.uuid4(),data,'benchmark.jpg' if name=='jpeg' else 'benchmark.png','image/jpeg' if name=='jpeg' else 'image/png')
            elapsed=time.perf_counter()-start
            matches={key: (' '.join(str(result.extracted_fields.get(key) or '').split()) == ' '.join(str(value).split())) for key,value in truth.items()}
            critical=('khasra_number','owner_name','area_in_hectares','village','district','land_classification')
            item=dict(case=name,version=version,field_accuracy=round(sum(matches.values())/len(matches),3),
                      critical_accuracy=round(sum(matches[k] for k in critical)/len(critical),3),
                      confidence=result.confidence_score,seconds=round(elapsed,3),
                      incorrect_fields=[k for k,v in matches.items() if not v],
                      requires_review=(result.analysis or {}).get('requires_manual_review'),
                      corrections=[p['preprocessing'] for p in (result.analysis or {}).get('pages',[])])
            results.append(item);print(json.dumps(item),flush=True)
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(results,indent=2),encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline-provider');parser.add_argument('--output',default='benchmark-results.json')
    asyncio.run(run(parser.parse_args()))
