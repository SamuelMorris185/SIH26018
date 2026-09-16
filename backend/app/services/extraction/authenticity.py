"""Conservative forensic triage, NOT authenticity certification or synthetic-image detection.

Weights: editor metadata 5; local residual anomaly 20; edge inconsistency 20;
spatially coherent copy-move 40. Correlated residual/edge signals cap at 30.
HIGH requires score >=60 and evidence from at least two non-metadata families.
Recompression and missing EXIF never independently imply manipulation.
"""
import io
from collections import Counter
import cv2
import numpy as np
from PIL import Image
from .image_analysis import small_gray

DISCLAIMER = 'Image-forensics signals indicate risk and do not independently prove document authenticity.'


def risk_result(signals, warnings=None):
    families = {}
    for signal in signals:
        families[signal['family']] = families.get(signal['family'], 0) + signal['weight']
    score = min(100, sum(min(v, 30) if k == 'local_consistency' else v for k,v in families.items()))
    independent = len(set(families) - {'metadata'})
    level = 'HIGH' if score >= 60 and independent >= 2 else 'MEDIUM' if score >= 20 else 'LOW'
    return dict(risk_level=level, risk_score=score, signals=signals, warnings=warnings or [],
                requires_manual_review=level == 'HIGH', analysis_version='1.0-heuristic', disclaimer=DISCLAIMER,
                limitations=['Synthetic-image origin could not be conclusively determined.',
                             'LOW risk is not proof of authenticity. Repeated forms, stamps, scans and compression can produce false positives.',
                             'No trained synthetic-image or resampling detector is installed.'])


class DocumentAuthenticityAnalyzer:
    def analyze(self, image, original_bytes=None):
        signals, warnings = [], []
        def add(code, family, weight, explanation, evidence):
            signals.append(dict(code=code, family=family, weight=weight, explanation=explanation, evidence=evidence))
        if original_bytes:
            try:
                with Image.open(io.BytesIO(original_bytes)) as original:
                    software = str(original.getexif().get(305, original.info.get('Software', '')))[:120]
                    if software:
                        add('SOFTWARE_METADATA','metadata',5,'Software metadata is present; editing/export software is also used for legitimate scans.', {'software':software})
            except Exception:
                warnings.append('Image metadata could not be read; this is not evidence of fraud.')
        g = small_gray(image, 1000)
        residual = cv2.absdiff(g, cv2.GaussianBlur(g,(5,5),0))
        lap = np.abs(cv2.Laplacian(g,cv2.CV_64F))
        # Compare only patches with similar ink density. Blank paper and table rules are excluded.
        patches = []
        for y in range(0,g.shape[0]-64,64):
            for x in range(0,g.shape[1]-64,64):
                p = g[y:y+64,x:x+64]
                ink = float(np.mean(p < 160))
                if .08 < ink < .45 and p.std() > 15:
                    patches.append((x,y,ink,float(residual[y:y+64,x:x+64].mean()),float(lap[y:y+64,x:x+64].mean())))
        if len(patches) >= 12:
            arr = np.array(patches)
            for index, code, label in [(3,'LOCAL_RESIDUAL','Local noise/edge residual'),(4,'EDGE_SHARPNESS','Text-edge sharpness')]:
                median = np.median(arr[:,index]); mad = np.median(np.abs(arr[:,index]-median)) + 1
                outliers = arr[(arr[:,index] > median+6*mad) & (arr[:,index] > median*2.5)]
                if 0 < len(outliers) < len(arr)*.2:
                    add(code,'local_consistency',20,f'{label} differs markedly in a small region; verify against the original.',
                        {'analysis_size':[g.shape[1],g.shape[0]], 'regions':outliers[:5,:2].astype(int).tolist(),'patch_size':64})
        # ORB: exclude nearby/repetitive descriptors; require coherent displacement and spatial spread.
        orb = cv2.ORB_create(nfeatures=700)
        keys, descriptors = orb.detectAndCompute(g,None)
        coherent = []
        if descriptors is not None and len(keys) > 30:
            matches = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(descriptors,descriptors,k=4)
            votes = []
            for candidates in matches:
                others = [m for m in candidates if m.queryIdx != m.trainIdx and m.distance < 28]
                if len(others) != 1: continue  # repeated glyphs/forms are ambiguous
                m = others[0]
                a,b = np.array(keys[m.queryIdx].pt),np.array(keys[m.trainIdx].pt)
                delta = b-a
                if np.linalg.norm(delta) < 100: continue
                if delta[0] < 0: delta = -delta
                votes.append((tuple(np.round(delta/12).astype(int)),a,b))
            if votes:
                displacement,n = Counter(v[0] for v in votes).most_common(1)[0]
                selected = [v for v in votes if v[0] == displacement]
                coords = np.array([v[1] for v in selected])
                if n >= 16 and np.ptp(coords[:,0]) > 70 and np.ptp(coords[:,1]) > 70:
                    coherent = [list(displacement),n]
        if coherent:
            add('COPY_MOVE','copy_move',40,'Spatially coherent duplicate image features detected. Repeated stamps or form content may also explain this.',
                {'displacement_bins_12px':coherent[0],'feature_matches':coherent[1]})
        result = risk_result(signals,warnings)
        result['input_type'] = 'image_unspecified'
        result['limitations'].append('Screenshot or monitor origin cannot be reliably inferred from image pixels alone.')
        return result
