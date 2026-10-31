"""Download verified official OpenCV Zoo models (internet required, run once).

Run in Windows CMD:
    cd backend
    py scripts\\download_models.py
Models are 0.23 MB (YuNet) and 38.7 MB (SFace). They are not in the ZIP.
"""
import hashlib
import os
from pathlib import Path
from urllib.request import Request, urlopen

MODELS = [
    ('face_detection_yunet_2023mar.onnx', 'face_detection_yunet',
     '8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4', 232589),
    ('face_recognition_sface_2021dec.onnx', 'face_recognition_sface',
     '0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79', 38696353),
]
DEST = Path(__file__).resolve().parents[1] / 'app' / 'models'


def download(filename, category, checksum, size):
    DEST.mkdir(parents=True, exist_ok=True)
    path = DEST / filename
    if path.exists() and path.stat().st_size == size and hashlib.sha256(path.read_bytes()).hexdigest() == checksum:
        print(f'Already verified: {filename}')
        return
    sources = [
        f'https://huggingface.co/opencv/opencv_zoo/resolve/main/models/{category}/{filename}?download=true',
        f'https://huggingface.co/opencv/{category}/resolve/main/{filename}?download=true',
        f'https://github.com/opencv/opencv_zoo/raw/refs/heads/main/models/{category}/{filename}',
    ]
    print(f'Downloading {filename} ({size / 1_000_000:.1f} MB)...', flush=True)
    tmp = path.with_suffix('.onnx.partial')
    last_error = None
    for index, url in enumerate(sources, 1):
        digest = hashlib.sha256()
        try:
            with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0 ReMindAI/1.1'}), timeout=120) as response, open(tmp, 'wb') as writer:
                written = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk: break
                    written += len(chunk)
                    if written > size:
                        raise RuntimeError('Received a file larger than the verified model.')
                    digest.update(chunk)
                    writer.write(chunk)
            if written != size or digest.hexdigest() != checksum:
                raise RuntimeError('Downloaded file did not match the official SHA-256 checksum.')
            os.replace(tmp, path)
            print(f'Verified and installed: {filename}', flush=True)
            return
        except Exception as exc:
            last_error = exc
            print(f'Mirror {index} failed: {str(exc)[:140]}', flush=True)
        finally:
            if tmp.exists(): tmp.unlink()
    raise RuntimeError(f'Could not download {filename} from all official sources. Last error: {last_error}')


if __name__ == '__main__':
    try:
        for params in MODELS:
            download(*params)
        print('\nBoth models installed! Refresh the ReMind app; no API restart should be needed.')
    except Exception as error:
        print(f'\nDownload failed: {error}')
        print('Manual alternative: download both .onnx files from https://huggingface.co/opencv/opencv_zoo/tree/main/models/')
        print(f'Put them in: {DEST}')
        raise SystemExit(1)
