"""Bounded, offline document image analysis. Scores are heuristics, not probabilities.

Quality: sharpness=min(100, Laplacian variance/2), contrast=min(100, std/40*100),
resolution=min(100, shortest edge/1000*100). Exposure measures dark/bright clipping;
white paper alone is never treated as glare. See OCR_ANALYSIS.md for limitations.
"""
import io
import math
import warnings
import cv2
import numpy as np
from PIL import Image, ImageOps
from app.core.config import settings
from app.core.exceptions import ExtractionProcessingError


def load_image(data: bytes) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.width * image.height > settings.OCR_MAX_PIXELS:
                    raise ExtractionProcessingError('Image exceeds the analysis pixel limit. Use a smaller scan.')
                image.load()
                image = ImageOps.exif_transpose(image)
                rgba = image.convert('RGBA')
                white = Image.new('RGBA', rgba.size, 'white')
                white.alpha_composite(rgba)
                return white.convert('RGB')
    except ExtractionProcessingError:
        raise
    except Exception as exc:
        raise ExtractionProcessingError('Corrupt or unreadable image. Upload a valid scan.') from exc


def small_gray(image, edge=1400):
    copy = image.convert('L')
    copy.thumbnail((edge, edge))
    return np.asarray(copy)


def boundary(gray):
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 40, 120)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = gray.shape
    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:8]:
        area = cv2.contourArea(c) / (h * w)
        poly = cv2.approxPolyDP(c, .025 * cv2.arcLength(c, True), True)
        if len(poly) != 4 or not cv2.isContourConvex(poly) or not .45 < area < .98:
            continue
        points = poly[:, 0].astype(np.float32)
        center = points.mean(axis=0)
        points = points[np.argsort(np.arctan2(points[:, 1]-center[1], points[:, 0]-center[0]))]
        points = np.roll(points, -np.argmin(points.sum(axis=1)), axis=0)
        sides = np.linalg.norm(points - np.roll(points, -1, axis=0), axis=1)
        if min(sides) < .2 * min(h, w):
            continue
        # Bright paper against darker surroundings; avoid cropping internal ruled tables.
        mask = np.zeros_like(gray); cv2.fillConvexPoly(mask, points.astype(np.int32), 255)
        if gray[mask > 0].mean() - gray[mask == 0].mean() < 18:
            continue
        return points, float(area)
    return None, None


def skew_angle(gray):
    ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    joined = cv2.dilate(ink, np.ones((1, 25), np.uint8))
    contours, _ = cv2.findContours(joined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    angles = []
    for contour in contours:
        (_, _), (w, h), angle = cv2.minAreaRect(contour)
        if min(w, h) < 3 or max(w, h) / max(1, min(w, h)) < 4:
            continue
        if angle > 45: angle -= 90
        if abs(angle) <= 12: angles.append(angle)
    return float(np.median(angles)) if len(angles) >= 4 else 0.0


def analyze_quality(image):
    g = small_gray(image)
    sharp = float(cv2.Laplacian(g, cv2.CV_64F).var())
    brightness, contrast = float(g.mean()), float(g.std())
    dark, white = float(np.mean(g < 12)), float(np.mean(g > 250))
    points, coverage = boundary(g)
    angle = skew_angle(g)
    # Only isolated saturated islands surrounded by darker paper are glare candidates.
    saturated = (g > 250).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(saturated)
    glare = 0.0
    for x, y, w, h, size in stats[1:count]:
        fraction = size / g.size
        if .01 < fraction < .35 and x > 5 and y > 5 and x+w < g.shape[1]-5 and y+h < g.shape[0]-5:
            patch = g[max(0,y-5):y+h+5, max(0,x-5):x+w+5]
            if np.percentile(patch, 10) < 190: glare += fraction
    sharpness = min(100., sharp / 2)
    lighting = max(0., 100 - max(0, 90-brightness) * 1.2 - dark * 100)
    contrast_score = min(100., contrast / 40 * 100)
    resolution = min(100., min(image.size) / 1000 * 100)
    score = round(.3*sharpness + .25*lighting + .25*contrast_score + .2*resolution)
    perspective = None
    if points is not None:
        sides = np.linalg.norm(points - np.roll(points,-1,axis=0),axis=1)
        perspective = round(100 * min(sides[0],sides[2])/max(sides[0],sides[2]) * min(sides[1],sides[3])/max(sides[1],sides[3]),1)
    issues = []
    if sharpness < 30: issues.append('Image is blurry; hold the camera steady and retake if text is unreadable.')
    if brightness < 65: issues.append('Too dark; increase even lighting.')
    if contrast_score < 30: issues.append('Low text/background contrast; enhancement will be attempted.')
    if min(image.size) < 600: issues.append('Low resolution; move closer. Upscaling cannot recover missing detail.')
    if glare > .04: issues.append('Possible glare is covering part of the document. Retake without direct reflection.')
    if abs(angle) > 1: issues.append('Text is tilted; deskew will be attempted.')
    if points is not None: issues.append('Document boundary detected; perspective correction available.')
    severe = sharpness < 8 or min(image.size) < 250 or brightness < 35 or glare > .12
    return dict(quality_score=score, blur_score=round(sharpness,1), brightness_score=round(lighting,1),
                contrast_score=round(contrast_score,1), resolution_score=round(resolution,1),
                skew_angle=round(angle,2), glare_score=round(glare*100,1),
                document_coverage_score=round(coverage*100,1) if coverage else None,
                perspective_score=perspective, issues=issues,
                measurements=dict(laplacian_variance=round(sharp,2), mean_luminance=round(brightness,2),
                                  luminance_std=round(contrast,2), dark_fraction=round(dark,4), saturated_fraction=round(white,4)),
                recommended_action='RECAPTURE_RECOMMENDED' if severe else 'AUTO_CORRECT' if issues else 'ACCEPT')


def correct_image(image, quality):
    original_size = image.size
    g = small_gray(image)
    points, coverage = boundary(g)
    changes = []
    if points is not None:
        points *= image.width / g.shape[1]
        tl, tr, br, bl = points
        w = int(max(np.linalg.norm(tr-tl), np.linalg.norm(br-bl)))
        h = int(max(np.linalg.norm(bl-tl), np.linalg.norm(br-tr)))
        matrix = cv2.getPerspectiveTransform(points, np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]]))
        image = Image.fromarray(cv2.warpPerspective(np.asarray(image), matrix, (w,h), borderValue=(255,255,255)))
        changes.append('perspective_corrected')
    gray = image.convert('L')
    angle = skew_angle(small_gray(gray))
    if .4 < abs(angle) < 12:
        gray = gray.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=255)
        changes.append('deskewed')
    # Bound all OCR copies to 2400px; upscale small originals at most 2x.
    scale = min(2., 1600 / gray.width) if gray.width < 1200 else min(1., 2400 / max(gray.size))
    if scale != 1:
        gray = gray.resize((int(gray.width*scale), int(gray.height*scale)), Image.Resampling.LANCZOS)
        changes.append('rescaled')
    return gray, dict(operations=changes, deskew_angle=round(angle,2), original_size=list(original_size),
                      corrected_size=list(gray.size), boundary_confidence='conservative_quad' if coverage else 'not_detected')


def variants(gray, quality):
    yield 'grayscale', gray, 3
    arr = np.asarray(gray)
    clahe = cv2.createCLAHE(clipLimit=2., tileGridSize=(8,8)).apply(arr)
    yield 'contrast', Image.fromarray(clahe), 6
    if quality['brightness_score'] < 65:
        result = cv2.adaptiveThreshold(clahe,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,31,12)
        yield 'adaptive', Image.fromarray(result), 4
    else:
        result = cv2.threshold(clahe,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]
        yield 'otsu', Image.fromarray(result), 11
