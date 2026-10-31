"""Local face-presence detector (NOT identity recognition).

YuNet is preferred. If it finds nothing, try Haar face-presence detection.
Haar rectangles have no facial landmarks, so can never identify a person.
"""
from pathlib import Path
from threading import RLock
import cv2

MODEL_FILE = Path(__file__).resolve().parent / 'models' / 'face_detection_yunet_2023mar.onnx'
_LOCK = RLock()
_cached_signature = None
_yunet = None
_frontal = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
_alt = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml')
if _frontal.empty():
    raise RuntimeError('OpenCV frontal face cascade is missing')


def _get_yunet():
    global _cached_signature, _yunet
    signature = (MODEL_FILE.stat().st_size, MODEL_FILE.stat().st_mtime_ns) if MODEL_FILE.exists() else None
    if signature != _cached_signature:
        _cached_signature, _yunet = signature, None
        if signature and hasattr(cv2, 'FaceDetectorYN_create'):
            try:
                _yunet = cv2.FaceDetectorYN_create(str(MODEL_FILE), '', (320, 320), .65, .3, 100)
            except (cv2.error, OSError, ValueError):
                pass
    return _yunet


def detect_faces(image):
    """Return boxes in original image pixel coordinates and the detector name."""
    height, width = image.shape[:2]
    if height < 80 or width < 80:
        return [], 'image_too_small'
    scale = min(1., 800. / max(height, width))
    if scale < 1.:
        resized = cv2.resize(image, (max(1, round(width*scale)), max(1, round(height*scale))), interpolation=cv2.INTER_AREA)
    else:
        resized = image
    h, w = resized.shape[:2]
    with _LOCK:
        detector = _get_yunet()
        if detector is not None:
            try:
                detector.setInputSize((w, h))
                _, result = detector.detect(resized)
                boxes = [tuple(float(v) for v in row[:4]) for row in result] if result is not None else []
                clipped = _clip_and_scale(boxes, width, height, scale)
                if clipped:
                    return clipped, 'yunet'
            except cv2.error:
                pass
        # Offline fallback improves *presence* recall. It never supplies
        # identities or features to the SFace matcher.
        gray = cv2.equalizeHist(cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY))
        min_size = max(26, round(min(h, w) * 0.055))
        boxes = _frontal.detectMultiScale(gray, 1.08, 4, minSize=(min_size, min_size))
        if not len(boxes) and not _alt.empty():
            boxes = _alt.detectMultiScale(gray, 1.08, 3, minSize=(min_size, min_size))
    # Keep the public API's detector label stable: callers expect 'haar' or 'yunet'.
    # Haar is *presence only*, never an identity source.
    return _clip_and_scale(boxes, width, height, scale), 'haar'


def _clip_and_scale(boxes, orig_w, orig_h, scale):
    output = []
    for x, y, w, h in boxes:
        left = min(max(0, round(x / scale)), orig_w - 1)
        top = min(max(0, round(y / scale)), orig_h - 1)
        right = min(orig_w, max(left + 1, round((x+w)/scale)))
        bottom = min(orig_h, max(top + 1, round((y+h)/scale)))
        if right - left < 16 or bottom - top < 16:
            continue
        box = (left, top, right-left, bottom-top)
        if any(_iou(box, previous) > .4 for previous in output):
            continue
        output.append(box)
    return output[:10]


def _iou(a, b):
    left, top = max(a[0],b[0]), max(a[1],b[1])
    right = min(a[0]+a[2],b[0]+b[2])
    bottom = min(a[1]+a[3],b[1]+b[3])
    intersection = max(0,right-left)*max(0,bottom-top)
    return intersection / max(1,a[2]*a[3]+b[2]*b[3]-intersection)
