"""Local face debugging (no upload, no database writes).

Usage:
  python scripts/face_debug.py "C:\\photos\\front.jpg"
  python scripts/face_debug.py "C:\\photos\\front.jpg" "C:\\photos\\side.jpg"
Second photo, if provided, prints descriptor cosine similarity for two
consenting photographs. This is not an identity probability.
"""
from pathlib import Path
import sys
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.face_identity import model_status, extract_enrollment, cosine_similarity
from app.vision import detect_faces


def analyze(path):
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        print(f"ERROR: Could not open image: {path}")
        return None
    print(f"Photo: {path.name}, resolution {image.shape[1]} x {image.shape[0]}")
    rects, detector = detect_faces(image)
    print(f"  Face presence: {len(rects)} candidate(s) using {detector}.")
    if len(rects) != 1:
        print("  For enrollment, use a sharp portrait with ONE large, unobstructed face.")
        return None
    try:
        descriptor = extract_enrollment(image)
        print("  SFace landmarks and quality: PASS (suitable for enrollment)")
        return descriptor
    except (RuntimeError, ValueError) as error:
        print(f"  SFace landmarks / quality: NOT READY: {error}")
        return None


def main():
    print("ReMindAI | Local Face Diagnostics")
    status = model_status()
    print("YuNet/SFace ready:", status["ready"])
    if not status["ready"]:
        print("Run MODEL_SETUP_WINDOWS.cmd; details:", status["message"])
        return 2
    if len(sys.argv) not in (2, 3):
        print('Usage: python scripts/face_debug.py "photo1.jpg" ["photo2.jpg"]')
        print("No images are uploaded or saved by this tool.")
        return 2
    images = [Path(p).expanduser() for p in sys.argv[1:]]
    vectors = [analyze(path) for path in images]
    if len(vectors) == 2 and all(v is not None for v in vectors):
        score = cosine_similarity(vectors[0], vectors[1])
        print(f"Similarity between the two supplied photos: {score:.3f} (NOT a probability).")
        print("This test is useful for checking lighting/angles, not proving identity.")
    print("\nCamera tips: eye level, front lighting, face ~120+ px wide;")
    print("enroll 3–5 different photos per consenting person. Unknown is intentional when uncertain.")
    return 0 if vectors[0] is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
