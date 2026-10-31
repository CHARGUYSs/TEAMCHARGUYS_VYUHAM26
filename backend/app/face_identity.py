"""Private, opt-in face matching against explicitly enrolled profiles.

Uses OpenCV Zoo YuNet for 5-landmark face detection and SFace for descriptors.
No remote inference service. Unknown faces are not assigned a name.
This is a hackathon demonstrator, not a safety-critical identifier.
"""
import json
import os
from pathlib import Path
from threading import RLock

import cv2
import numpy as np

MODEL_DIR = Path(__file__).resolve().parent / 'models'
DETECTOR_FILE = MODEL_DIR / 'face_detection_yunet_2023mar.onnx'
RECOGNIZER_FILE = MODEL_DIR / 'face_recognition_sface_2021dec.onnx'
MODEL_LOCK = RLock()
_model_key = None
_detector = None
_recognizer = None
_model_error = None
# More conservative than the OpenCV LFW reference (0.363). Threshold is tunable
# and must be evaluated on your actual camera/data; never a probability.
MATCH_THRESHOLD = float(os.getenv('FACE_MATCH_THRESHOLD', '0.46'))
MATCH_MARGIN = float(os.getenv('FACE_MATCH_MARGIN', '0.04'))
MAX_SIDE = 960


def model_status():
    with MODEL_LOCK:
        _load_models()
        return {
            'ready': _detector is not None and _recognizer is not None,
            'detector_installed': DETECTOR_FILE.is_file(),
            'recognizer_installed': RECOGNIZER_FILE.is_file(),
            'message': _model_error or 'Recognition models loaded. Enroll photos to match faces locally.',
            'match_threshold': MATCH_THRESHOLD,
        }


def _load_models():
    global _model_key, _detector, _recognizer, _model_error
    # Lazy reload if someone runs the downloader while the app is already open.
    key = tuple((path.stat().st_mtime_ns, path.stat().st_size) if path.is_file() else None
                for path in (DETECTOR_FILE, RECOGNIZER_FILE))
    if _model_key == key:
        return
    _model_key, _detector, _recognizer, _model_error = key, None, None, None
    if None in key:
        _model_error = 'Recognition models not installed. Run: python scripts/download_models.py in backend, then refresh.'
        return
    if not (hasattr(cv2, 'FaceDetectorYN_create') and hasattr(cv2, 'FaceRecognizerSF_create')):
        _model_error = 'OpenCV installation does not support YuNet/SFace. Reinstall backend requirements.'
        return
    try:
        _detector = cv2.FaceDetectorYN_create(str(DETECTOR_FILE), '', (320, 320), 0.65, 0.3, 100)
        _recognizer = cv2.FaceRecognizerSF_create(str(RECOGNIZER_FILE), '')
    except (cv2.error, OSError, ValueError) as exc:
        _detector = _recognizer = None
        _model_error = f'Cannot initialize model: {str(exc)[:160]}'


def _faces_with_features(image):
    """Caller must hold MODEL_LOCK. Coordinates are in original image pixels."""
    height, width = image.shape[:2]
    scale = min(1.0, MAX_SIDE / max(height, width))
    resized = cv2.resize(image, (round(width*scale), round(height*scale)), interpolation=cv2.INTER_AREA) if scale < 1 else image
    h, w = resized.shape[:2]
    _detector.setInputSize((w, h))
    _, found = _detector.detect(resized)
    output = []
    if found is None:
        return output
    for detected in found[:12]:
        x, y, fw, fh = [float(v) / scale for v in detected[:4]]
        if fw < 28 or fh < 28 or x + fw <= 0 or y + fh <= 0:
            continue
        x1, y1 = max(0., x), max(0., y)
        x2, y2 = min(float(width), x + fw), min(float(height), y + fh)
        if x2 <= x1 or y2 <= y1:
            continue
        # Feature alignment must use the same scale as the landmarks; pass resized.
        try:
            aligned = _recognizer.alignCrop(resized, detected)
            feature = _recognizer.feature(aligned).reshape(-1).astype(np.float32)
            norm = float(np.linalg.norm(feature))
            if norm < 1e-8 or not np.isfinite(feature).all():
                continue
            feature /= norm
        except cv2.error:
            continue
        output.append({
            'box': {'x': round(x1 / width, 5), 'y': round(y1 / height, 5),
                    'width': round((x2-x1) / width, 5),
                    'height': round((y2-y1) / height, 5)},
            'vector': feature,
        })
    return output


def extract_enrollment(image):
    """Returns embedding or raises ValueError with an actionable description."""
    with MODEL_LOCK:
        _load_models()
        if _detector is None or _recognizer is None:
            raise RuntimeError(_model_error or 'Models unavailable')
        faces = _faces_with_features(image)
    if len(faces) != 1:
        raise ValueError('Use a well-lit photo with exactly one visible face.' if not faces else 'More than one face was found. Crop to one person.')
    return faces[0]['vector'].tolist()


def recognize(image, templates):
    """templates are (person_id, person_name, relationship, vector) tuples.

    Outputs one result per face, including unknown. A person must match the
    enrolled sample with margin over competing enrolled profiles.
    """
    with MODEL_LOCK:
        _load_models()
        if _detector is None or _recognizer is None:
            raise RuntimeError(_model_error or 'Models unavailable')
        faces = _faces_with_features(image)
    validated = []
    for person_id, name, relationship, embedding in templates:
        try:
            arr = np.asarray(json.loads(embedding), dtype=np.float32)
            if arr.ndim == 1 and arr.size == 128 and np.isfinite(arr).all() and np.linalg.norm(arr) > 0:
                validated.append((person_id, name, relationship, arr / np.linalg.norm(arr)))
        except (ValueError, TypeError):
            continue
    results = []
    for face in faces:
        # Aggregate by person using their best enrolled sample.
        score_by_person = {}
        for person_id, name, relation, vec in validated:
            score = float(np.dot(face['vector'], vec))
            if person_id not in score_by_person or score > score_by_person[person_id][0]:
                score_by_person[person_id] = (score, name, relation)
        ranking = sorted(score_by_person.items(), key=lambda item: item[1][0], reverse=True)
        best_id, best_data = ranking[0] if ranking else (None, None)
        runner_up = ranking[1][1][0] if len(ranking) > 1 else -1.0
        accepted = bool(best_data and best_data[0] >= MATCH_THRESHOLD and best_data[0] - runner_up >= MATCH_MARGIN)
        results.append({**face['box'],
                        'status': 'matched' if accepted else 'unknown',
                        'person_id': best_id if accepted else None,
                        'name': best_data[1] if accepted else None,
                        'relationship': best_data[2] if accepted else None,
                        'similarity': round(best_data[0], 3) if best_data else None})
    return results
