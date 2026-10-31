"""Read-only checks for local ReMind AI face detection/recognition setup."""
import platform
import sys
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.face_identity import model_status
from app.vision import detect_faces


def main():
    print('ReMind AI setup diagnostics')
    print('Python:', platform.python_version())
    print('OpenCV:', cv2.__version__)
    print('YuNet API available:', hasattr(cv2, 'FaceDetectorYN_create'))
    print('SFace API available:', hasattr(cv2, 'FaceRecognizerSF_create'))
    state = model_status()
    print('Recognition ready:', state['ready'])
    print('Detector installed:', state['detector_installed'])
    print('Recognizer installed:', state['recognizer_installed'])
    print('Recognition message:', state['message'])
    test_image = np.full((320,320,3), 255, dtype=np.uint8)
    faces, mode = detect_faces(test_image)
    print('Blank-frame detector:', mode, '| detected faces:', len(faces))
    if not state['ready']:
        print('\nWHAT TO DO: Run MODEL_SETUP_WINDOWS.cmd from the project folder')
        print('and add 2-3 enrolled photos of each consenting person in Caregiver Studio.')
        return 1
    print('\nNEXT STEP: Enroll a person with permission and test their face in the browser.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
