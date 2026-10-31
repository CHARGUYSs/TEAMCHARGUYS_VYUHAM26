"""Optional higher-quality face-presence detector from OpenCV Zoo.

Run from backend/: python scripts/download_yunet.py
The project also works offline using the built-in OpenCV Haar cascades.
"""
import hashlib
from pathlib import Path
from urllib.request import urlopen

URL = 'https://huggingface.co/opencv/opencv_zoo/resolve/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx'
SHA256 = '8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4'
DEST = Path(__file__).resolve().parents[1] / 'app' / 'models' / 'face_detection_yunet_2023mar.onnx'


def main():
    DEST.parent.mkdir(parents=True, exist_ok=True)
    print('Downloading optional OpenCV Zoo YuNet face detector...')
    with urlopen(URL, timeout=30) as response:
        model = response.read(2_000_000)
    if hashlib.sha256(model).hexdigest() != SHA256:
        raise RuntimeError('Downloaded model hash does not match the published SHA-256. File not installed.')
    DEST.write_bytes(model)
    print(f'Saved verified YuNet model to {DEST}. Restart FastAPI to activate it.')


if __name__ == '__main__':
    main()
