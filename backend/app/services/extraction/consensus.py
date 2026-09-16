"""Literal field voting across correlated OCR variants; never fuzzy-correct identifiers."""
from collections import defaultdict
from app.core.config import settings
from app.schemas.extraction import categorize_confidence

CRITICAL_FIELDS = ('state','district','tehsil','village','khasra_number','khata_number','owner_name','area_in_hectares','land_classification')


def consensus(passes):
    fields, scores, evidence = {}, {}, {}
    for name in passes[0]['evidence']:
        groups = defaultdict(list)
        for item in passes:
            e = item['evidence'][name]
            if e.value not in (None, ''):
                # Whitespace only: spelling, punctuation and identifier characters stay literal.
                groups[' '.join(str(e.value).split())].append((item,e))
        if not groups:
            chosen = passes[0]['evidence'][name].model_copy(deep=True)
            chosen.value = None; chosen.normalized_value = None; chosen.confidence = 0
            chosen.requires_review = True
        else:
            ranked = sorted(groups.items(), key=lambda pair: sum(e.confidence for _,e in pair[1]),reverse=True)
            value, support = ranked[0]
            chosen = max(support,key=lambda pair:pair[1].confidence)[1].model_copy(deep=True)
            average = sum(e.confidence for _,e in support)/len(support)
            # No independence assumption or confidence inflation. Disagreement lowers confidence.
            total_weight = sum(e.confidence for group in groups.values() for _,e in group)
            agreement = sum(e.confidence for _,e in support)/max(.001,total_weight)
            chosen.confidence = round(average*(.7+.3*agreement),3)
            chosen.supporting_passes = [p['id'] for p,_ in support]
            chosen.page_numbers = sorted(set(p['page'] for p,_ in support))
            chosen.alternatives = [dict(value=v,confidence=round(max(e.confidence for _,e in group),3),
                                        passes=[p['id'] for p,_ in group]) for v,group in ranked[1:]]
            chosen.requires_review = chosen.confidence < settings.CONFIDENCE_THRESHOLD_HIGH or len(groups)>1
        chosen.category = categorize_confidence(chosen.confidence,settings.CONFIDENCE_THRESHOLD_HIGH,settings.CONFIDENCE_THRESHOLD_MEDIUM)
        chosen.source = 'OCR_CONSENSUS' if len(passes)>1 else passes[0].get('source','tesseract_ocr')
        fields[name] = chosen.value
        scores[name] = chosen.confidence
        evidence[name] = chosen
    return fields,scores,evidence,[n for n,s in scores.items() if s < settings.CONFIDENCE_THRESHOLD_MEDIUM]
