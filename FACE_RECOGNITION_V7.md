# ReMindAI v7 — Face detection and recognition guide

## What changed
- **More reliable face presence:** OpenCV YuNet detector first, with illumination correction and Haar-based *presence-only* fallback when landmarks cannot be found. Haar boxes never generate an identity.
- **Opt-in identity recognition:** YuNet landmarks + OpenCV SFace embedding from 3–5 DIFFERENT consented portraits of each person, not an illustrated profile image.
- **Safer similarity checks:** Match must pass a score threshold and separation from the nearest competing person. When multiple portraits are enrolled, at least two portraits must support the match. This avoids a name being chosen solely because one outlier portrait scored high.
- **Quality checks:** Enrollment rejects missing, multiple, tiny, poorly focused and improperly lit faces. Live identity matching rejects severely blurred, dark/bright or tiny captures and gives plain-language feedback.
- **Live-view stability:** The browser waits for three consecutive frames with the same identified person before displaying a name or speaking it.
- **Identity statuses:** `matched`, `unknown` with `not_enrolled`, `low_similarity`, `ambiguous`, `inconsistent_samples`, `low_quality`, and `detection_only` reasons.
- **Repeatable local diagnostics:** `CHECK_FACE_SETUP_WINDOWS.cmd`, `MODEL_SETUP_WINDOWS.cmd` and `FACE_DEBUG_WINDOWS.cmd`.

## Windows: start from the updated ZIP
1. Extract ZIP in its own folder. Keep your existing original project / data backup separately.
2. Run `SETUP_WINDOWS.cmd` once. It creates a Python environment, installs frontend packages and checks recognition weights. Internet may be needed on your PC.
3. Run `CHECK_FACE_SETUP_WINDOWS.cmd` and confirm the two models are present and supported by OpenCV.
4. If models are missing, run `MODEL_SETUP_WINDOWS.cmd` and restart the API.
5. Run `START_WINDOWS.cmd`. The web page opens at http://127.0.0.1:5173.
6. In **Caregiver Studio → Loved ones & face enrollment**, select the correct profile and obtain the person's informed permission. Upload 3–5 DIFFERENT sharp portraits: front-facing, a little to the left, a little to the right, consistent front lighting. Do not enroll illustrations, group photos or the same photo duplicated.
7. On **Home → Face recognition**, choose **Upload a photo** first with a NEW photo (not an enrollment copy). The result may say **Possible match** or **Unknown**. Confirm by consulting the person / caregiver.
8. Use **Start live camera** with a face filling a reasonable portion of the image. It requires 3 consistent results before a name is shown.
9. If results are wrong, remove that profile's face samples and enroll the correct person with varied real photos. Avoid changing thresholds without a consented dataset with both genuine and impostor cases.

## Photo diagnostic tool
Drag a clear JPEG/PNG of a consenting volunteer onto `FACE_DEBUG_WINDOWS.cmd`, or in Command Prompt:
```
FACE_DEBUG_WINDOWS.cmd "C:\photos\front.jpg"
```
For two images of a consenting volunteer:
```
FACE_DEBUG_WINDOWS.cmd "C:\photos\front.jpg" "C:\photos\left.jpg"
```
The diagnostic prints whether a face can be located and whether YuNet/SFace landmarks pass image-quality checks. Two-photo similarity is a *relative embedding score*, not a probability and not proof of identity.

## Troubleshooting
| Symptom | Likely cause | Remedy |
|---|---|---|
| Camera denied | Browser permissions / insecure address | Use localhost or HTTPS; grant webcam permission; close other apps using the camera |
| AI models not ready | ONNX files missing or OpenCV incompatible | Run model setup and diagnostic; restart backend |
| No face detected | Backlighting, face too far, motion blur, profile view | Use front lighting, face camera directly and move closer |
| Detected but Unknown | No enrolled portrait, low similarity, ambiguous profiles, poor capture, inconsistent enrollment | Enroll 3–5 quality varied portraits, and remove mislabeled face samples |
| Name changes or flickers | Single low-quality frame / multiple people | One face at a time; hold still for ~3 consistent checks; use upload-photo workflow first |
| Same person misnamed | Two profiles have similar/mislabeled samples | Check the caregiver profiles and remove incorrect enrollment samples; do not lower the match threshold to hide the issue |
| Bad boxes on extremely simple cartoon | Face presence models expect real faces | Test with consented real images rather than stylized images |

## Verification and limitations
- All 36 backend tests passed on Oct 31, 2026 using an isolated disposable test database (the uploaded `backend/remind_ai.db` was not used for testing).
- An installed ONNX model pair passed a local smoke check for **face presence and same-photo embedding consistency**. A same-photo check does *not* measure generalization to new photos, different lighting or a new camera.
- `frontend/src/App.jsx` passed TypeScript JSX syntax parsing. A full frontend build and webcam/browser test were **not** completed in this Linux runtime.
- **Cannot guarantee identity accuracy** without a diverse, consented test set, actual camera access and validated false-accept/false-reject rates. Face recognition should only assist with memories, never authenticate users, decide medication, unlock doors or replace caregiver confirmation.
- The app still uses a shared login between patient and caregiver. Face vectors are stored in an account-scoped SQLite table and are **not encrypted at rest**. Consult a security/privacy expert before real patient use.
- The v6 changes are retained. This package does not merge the separate Twilio SOS ZIP.
