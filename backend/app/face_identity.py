"""Consent-based, LOCAL face matching using OpenCV YuNet and SFace.

Face detection and identity matching are different operations. Match scores are
cosine similarities, NOT probabilities or medical/safety guarantees. Unknown /
uncertain is intentionally preferred to a wrong person's name.
"""
import json
import os
from pathlib import Path
from threading import RLock

import cv2
import numpy as np

MODEL_DIR = Path(__file__).resolve().parent / "models"
DETECTOR_FILE = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
RECOGNIZER_FILE = MODEL_DIR / "face_recognition_sface_2021dec.onnx"
MODEL_LOCK = RLock()
_model_key = None
_detector = None
_recognizer = None
_model_error = None

# OpenCV's nominal SFace cosine threshold is ~0.363 on a particular benchmark;
# it is not universal. Defaults prioritize fewer false names; tune only after
# measuring consenting people's images on the actual webcam.
MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.42"))
MATCH_MARGIN = float(os.getenv("FACE_MATCH_MARGIN", "0.06"))
MAX_SIDE = 1280
MIN_ENROLL_FACE = 70


def model_status():
    with MODEL_LOCK:
        _load_models()
        return {
            "ready": _detector is not None and _recognizer is not None,
            "detector_installed": DETECTOR_FILE.is_file(),
            "recognizer_installed": RECOGNIZER_FILE.is_file(),
            "message": _model_error or "Models ready. Enroll 3-5 varied, clear, consented face photos per person.",
            "match_threshold": MATCH_THRESHOLD,
            "match_margin": MATCH_MARGIN,
            "recommended_samples": 3,
            "max_samples": 8,
            "note": "Similarity is NOT a probability of identity. Unknown faces require caregiver confirmation.",
        }


def _load_models():
    global _model_key, _detector, _recognizer, _model_error
    key = tuple((path.stat().st_mtime_ns, path.stat().st_size) if path.is_file() else None
                for path in (DETECTOR_FILE, RECOGNIZER_FILE))
    if _model_key == key:
        return
    _model_key, _detector, _recognizer, _model_error = key, None, None, None
    if None in key:
        _model_error = "Recognition models missing. Run MODEL_SETUP_WINDOWS.cmd and restart."
        return
    if not (hasattr(cv2, "FaceDetectorYN_create") and hasattr(cv2, "FaceRecognizerSF_create")):
        _model_error = "OpenCV YuNet/SFace is unavailable. Reinstall backend requirements."
        return
    try:
        # Slightly lower detector confidence improves recall on webcam frames.
        # Identity acceptance remains conservative and independent of this.
        _detector = cv2.FaceDetectorYN_create(str(DETECTOR_FILE), "", (320, 320), 0.55, 0.3, 100)
        _recognizer = cv2.FaceRecognizerSF_create(str(RECOGNIZER_FILE), "")
    except (cv2.error, OSError, ValueError) as exc:
        _detector = _recognizer = None
        _model_error = f"Could not load face models: {str(exc)[:160]}"


def _enhance_dark(image):
    """CLAHE can help YuNet find a face when a frame is underexposed."""
    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return cv2.cvtColor(cv2.merge((clahe.apply(y), cr, cb)), cv2.COLOR_YCrCb2BGR)


def _faces_with_features(image):
    """Caller holds MODEL_LOCK. Return normalized box, feature and diagnostics."""
    height, width = image.shape[:2]
    if min(height, width) < 80:
        return []
    scale = min(1.0, MAX_SIDE / max(height, width))
    resized = (cv2.resize(image, (max(1, round(width * scale)),
                                  max(1, round(height * scale))),
                          interpolation=cv2.INTER_AREA) if scale < 1 else image)
    h, w = resized.shape[:2]
    _detector.setInputSize((w, h))
    _, found = _detector.detect(resized)
    working = resized
    # Avoid silently substituting Haar detections into SFace: it needs 5 YuNet
    # landmarks for correct alignment. Retry using illumination correction only.
    # Try local contrast correction when the first pass misses a face. This
    # catches backlit / flat webcams as well as dim rooms, without lowering
    # the identity-matching threshold or relying on face-like Haar boxes.
    if (found is None or len(found) == 0) and (
        float(np.mean(resized)) < 145 or float(np.mean(resized)) > 195
        or float(np.std(cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY))) < 48
    ):
        working = _enhance_dark(resized)
        _, found = _detector.detect(working)
    if found is None:
        return []
    output = []
    for detected in sorted(found, key=lambda f: float(f[14]), reverse=True)[:12]:
        x, y, fw, fh = [float(v) / scale for v in detected[:4]]
        if fw < 28 or fh < 28:
            continue
        x1, y1 = max(0., x), max(0., y)
        x2, y2 = min(float(width), x + fw), min(float(height), y + fh)
        if x2 <= x1 or y2 <= y1:
            continue
        crop = image[int(y1):max(int(y1)+1, int(y2)), int(x1):max(int(x1)+1, int(x2))]
        if crop.size == 0:
            continue
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        side = min(x2 - x1, y2 - y1)
        try:
            aligned = _recognizer.alignCrop(working, detected)
            feature = _recognizer.feature(aligned).reshape(-1).astype(np.float32)
            norm = float(np.linalg.norm(feature))
            if norm < 1e-8 or not np.isfinite(feature).all():
                continue
            feature /= norm
        except cv2.error:
            continue
        advice = []
        if side < MIN_ENROLL_FACE:
            advice.append("Move closer so the face fills more of the frame.")
        if brightness < 52:
            advice.append("Move to brighter, even lighting.")
        if brightness > 232:
            advice.append("Avoid strong backlighting or overexposure.")
        if sharpness < 22:
            advice.append("Hold the camera steady and focus on the face.")
        output.append({
            "box": {"x": round(x1 / width, 5), "y": round(y1 / height, 5),
                    "width": round((x2-x1) / width, 5),
                    "height": round((y2-y1) / height, 5)},
            "vector": feature,
            "quality": {
                "face_size_px": int(side),
                "brightness": round(brightness, 1),
                "sharpness": round(sharpness, 1),
                "detection_score": round(float(detected[14]), 3),
                "advice": advice,
            },
        })
    return output


def extract_enrollment(image):
    """Return descriptor or reject photographs unsuitable for enrollment."""
    with MODEL_LOCK:
        _load_models()
        if _detector is None or _recognizer is None:
            raise RuntimeError(_model_error or "Models unavailable")
        faces = _faces_with_features(image)
    if len(faces) != 1:
        raise ValueError("No clear face found. Use a sharp, well-lit, front-facing portrait." if not faces
                         else "Several faces detected. Crop to just the person being enrolled.")
    quality = faces[0].get("quality", {})
    if quality.get("advice"):
        raise ValueError("Face photo needs improvement: " + " ".join(quality["advice"]))
    return faces[0]["vector"].tolist()


def _decode_template(embedding):
    try:
        arr = np.asarray(json.loads(embedding) if isinstance(embedding, str) else embedding,
                         dtype=np.float32)
        norm = float(np.linalg.norm(arr))
        if arr.shape == (128,) and np.isfinite(arr).all() and norm > 1e-9:
            return arr / norm
    except (TypeError, ValueError, OverflowError):
        pass
    return None


def cosine_similarity(first, second):
    """Used for detecting repeated enrollment photos, not for authentication."""
    a = _decode_template(first)
    b = _decode_template(second)
    return float(np.dot(a, b)) if a is not None and b is not None else None


def recognize(image, templates):
    """Find opted-in familiar faces. Unknown / ambiguous never returns a name.

    templates: (person_id, display_name, relationship, JSON-descriptor).
    """
    with MODEL_LOCK:
        _load_models()
        if _detector is None or _recognizer is None:
            raise RuntimeError(_model_error or "Models unavailable")
        faces = _faces_with_features(image)
    enrolled = {}
    for person_id, name, relationship, embedding in templates:
        arr = _decode_template(embedding)
        if arr is not None:
            person = enrolled.setdefault(person_id, {"name": name, "relationship": relationship, "vectors": []})
            person["vectors"].append(arr)
    results = []
    for face in faces:
        ranking = []
        for person_id, person in enrolled.items():
            scores = sorted((float(np.dot(face["vector"], v)) for v in person["vectors"]), reverse=True)
            # Use several examples without letting one lucky sample completely
            # override a disagreement among that person's own samples.
            score = scores[0] if len(scores) == 1 else (0.8 * scores[0] + 0.2 * scores[1])
            ranking.append((person_id, score, person))
        ranking.sort(key=lambda item: item[1], reverse=True)
        best = ranking[0] if ranking else None
        runner_up = ranking[1][1] if len(ranking) > 1 else -1.
        score = best[1] if best else None
        # With several reference portraits, require more than one sample to
        # support an identity. A single accidental high score is insufficient.
        agreed = True
        if best and len(best[2]["vectors"]) >= 2:
            all_scores = sorted((float(np.dot(face["vector"], v)) for v in best[2]["vectors"]), reverse=True)
            agreed = all_scores[1] >= max(0.22, MATCH_THRESHOLD - 0.12)
        quality = face.get("quality", {})
        poor_frame = (
            quality.get("sharpness", 999) < 12
            or quality.get("brightness", 120) < 35
            or quality.get("brightness", 120) > 243
            or quality.get("face_size_px", 1000) < 45
        )
        accepted = bool(best and score >= MATCH_THRESHOLD
                        and score - runner_up >= MATCH_MARGIN
                        and agreed and not poor_frame)
        if not best:
            reason = "not_enrolled"
        elif score < MATCH_THRESHOLD:
            reason = "low_similarity"
        elif score - runner_up < MATCH_MARGIN:
            reason = "ambiguous"
        elif poor_frame:
            reason = "low_quality"
        elif not agreed:
            reason = "inconsistent_samples"
        else:
            reason = "matched"
        result = {
            **face["box"],
            "status": "matched" if accepted else "unknown",
            "person_id": best[0] if accepted else None,
            "name": best[2]["name"] if accepted else None,
            "relationship": best[2]["relationship"] if accepted else None,
            "similarity": round(score, 3) if score is not None else None,
            "reason": reason,
            "quality_hint": " ".join(face.get("quality", {}).get("advice", [])),
            "enrolled_samples": len(best[2]["vectors"]) if accepted else 0,
        }
        results.append(result)
    return results
