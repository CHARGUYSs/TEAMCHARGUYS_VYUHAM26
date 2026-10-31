# ReMindAI v7 — Face recognition reliability update

**Face detection and recognition upgrade:** Safer multi-photo matching, clearer image-quality hints, contrast fallback, and fixed face-presence regression test. **Start with [FACE_RECOGNITION_V7.md](FACE_RECOGNITION_V7.md)** for detailed Windows steps; [TEST_REPORT_V7.md](TEST_REPORT_V7.md) explains verification and limitations. Keep a copy of your original database before replacing any files.

> **New in v6:** Refreshable personalized questions, caregiver-scheduled tasks with date ordering, private photo/video uploads to memories, chronological upcoming activities/reminders, and a transparent non-clinical tracking phase. [See V6_UPDATES.md](V6_UPDATES.md) for exact behavior, testing and limitations.

# ReMind AI — Patient Activity Monitor (Hackathon MVP)

A patient-friendly memory companion with local face detection, **opt-in identification of enrolled people** when recognition models are installed, reminders, saved family/memory/object records, voice input/readout, and an expanded caregiver dashboard that shows **recent questions, requested objects (pen, keys, glasses), recurring topics, activity history, follow-ups, and voluntary caregiver notes**.

## Quick setup on Windows (CMD)

1. Extract the ZIP into a short folder path, e.g. `C:\ReMindAI` (avoid putting it inside another ZIP).
2. Install **Python 3.10+** (with the `py` launcher) and **Node.js 20+**.
3. Double-click **`SETUP_WINDOWS.cmd`**. It installs the Python and web dependencies, then automatically attempts to download both face models (~39 MB, internet required). If the model download is blocked, setup still finishes with an explicit warning.
4. Double-click **`START_WINDOWS.cmd`**. Keep the two console windows open.
5. Open **http://127.0.0.1:5173** in Chrome or Edge. Use `127.0.0.1` or `localhost` for camera permission; ordinary HTTP LAN addresses are not secure contexts for the webcam.
6. Click **Try the interactive demo**. The demo is local-only; it creates illustrative family profiles and a made-up question history.
7. On the face-recognition screen, check **AI models ✓**. If not ready, use **Install AI models** or double-click **`MODEL_SETUP_WINDOWS.cmd`**.
8. In **Caregiver Studio → Loved ones & face enrollment**, create a profile for a *consenting* volunteer, then upload **2–3 real, clear face photos** with permission. (The illustrated sample faces are **not** actual enrolled identities.)
9. Click **Recognize a face** → **Start live camera** (allow camera access), or **Upload a photo**. The app can show a name only after models and enrollment are both ready. If uncertain, it says *Unknown face*.
10. Open **Find my things**, type **pen**, and click **Find this item**. Or ask **“Where is my pen?”** on the patient home screen. Both actions add a timestamped object request.
11. In **Caregiver Studio**, open **Patient activity monitor**. Find recently asked objects, recently asked questions, most requested objects, missing saved locations, follow-up suggestions, daily activity, a combined timeline, and caregiver notes.
12. Optional: after a face is matched against an enrolled profile, choose **Save this profile reminder** to place a dated, *patient-confirmed* reminder in the caregiver dashboard. This is **not evidence** that a real visit occurred.

### If face detection or face identification does not work

Run **`CHECK_FACE_SETUP_WINDOWS.cmd`**. It checks installed AI model files, OpenCV functionality, and the fallback detector. There are **three separate checks**:

| Stage | What works | What to check |
| --- | --- | --- |
| Webcam | Live video appears | Chrome/Edge permission; open on `http://127.0.0.1:5173`; close Zoom/Meet |
| Face detection | A face box appears | Good front lighting; face close enough; YuNet preferable; offline Haar fallback available |
| Face identification | An *enrolled* name + relationship appears | **Both** YuNet + SFace models, real enrollment photos, only one clear face in enrollment, 2–3 angles |

If camera permissions are denied, use **Upload a photo**. If AI models are missing, the camera can still say *face detected* but **cannot truthfully identify a person**. Do not treat detection as identification.

One-time model download alternatives:

```bat
cd /d C:\ReMindAI\backend
.venv\Scripts\python.exe scripts\download_models.py
```

The downloader retries official OpenCV/Hugging Face locations and checks model size and SHA-256. If network policies block all sources, download the **actual** ONNX model files (not LFS pointers) from these official pages and save under `backend\app\models\`:

- [YuNet face detector, 2023mar](https://huggingface.co/opencv/opencv_zoo/blob/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx)
- [SFace face recognizer, 2021dec](https://huggingface.co/opencv/opencv_zoo/blob/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx)

The SHA-256 hashes are defined in `backend/scripts/download_models.py`. This v6 ZIP **includes the ONNX model files** from the provided v5 archive, so a fresh model download should not be needed. In the app, use **Refresh status** after installation.

## Patient activity monitor (new in v4)

- **Recently asked questions:** timestamp, question text, input method, and whether a saved answer was available.
- **Recently requested objects:** e.g. **pen, keys, glasses**, with time, whether the query was spoken/typed or used Object Finder, and whether a caregiver-saved location exists.
- **Most requested objects:** frequency counts and a chart. Unknown objects like “wallet” still show up so caregivers know which locations to add.
- **Caregiver follow-ups:** frequently unanswered questions and objects with no saved location, based only on app usage.
- **Daily activity and timeline:** 7/30/90 days or all history; filter questions, object requests, user-saved identity prompts, and caregiver notes.
- **Caregiver notes:** manually add or delete a dated note, e.g. “The pen is in the desk organizer.” These are manually written, not AI-generated clinical observations.
- **User-saved identity prompts (optional):** after a possible face match, the patient may explicitly save that enrolled profile for later caregiver review. It is **not proof** the person was physically present. No face video is stored in the activity monitor.
- **Privacy controls:** download object requests as CSV, erase object request history, delete individual caregiver notes. Question history retains its separate CSV/export/delete controls. All results are filtered by signed-in account.

**Critical limitation:** The Object Finder reads *saved locations*. This version does **not** identify a pen from a camera image or know where an object physically is. The dashboard says **“objects asked about”**, never “objects seen/detected.” A future version would require a separate, tested object-recognition model for real camera detections.

### Demo exercise

1. Open patient home and ask **“Where is my pen?”** twice.
2. Go to **Find my things** and select **Pen** and **Wallet**.
3. Open **Caregiver Studio → Patient activity monitor**. Pen should be near the top of **Most requested objects**; the missing Wallet location should appear in **Caregiver follow-ups**.
4. Add a caregiver note such as **“Please keep the pen on the desk.”**
5. Review the unified timeline and recent-question list. Try the time filter and **Export object CSV**.

## Caregiver analytics (new)

Within the signed-in demo account, every successful `/api/question` request is saved with the question text, normalized form (to group punctuation/case variants), category, answer availability, entry method, and time. The dashboard provides:

- Total number of questions, different questions, answered from saved records, and questions needing caregiver input.
- Most repeated questions with counts, topic distribution, and a recent-question feed.
- A daily activity chart, filter for **7 / 30 / 90 days / all time**, **CSV export** with spreadsheet-formula protection, and **Clear history**.
- Data is **user-scoped** in SQLite. It is **usage analytics, not a clinical assessment, diagnosis, or evidence of cognitive decline**. For the hackathon, use invented demo questions. Question and object-request text may be sensitive; do not publish exported files or the local SQLite database.

The demo seeds a dozen **fictional** questions and several invented object lookups for the chart. These show how the interface behaves and are not a real user's data.

## Commands (alternative to double-click)

In the first CMD window:

```bat
cd /d C:\ReMindAI\backend
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts\download_models.py
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second CMD window:

```bat
cd /d C:\ReMindAI\frontend
npm ci
npm run dev
```

API health: http://127.0.0.1:8000/api/health · API docs: http://127.0.0.1:8000/docs.

## Test and diagnostic notes

Run from `backend`:

```bat
.venv\Scripts\python.exe scripts\verify_setup.py
```

Automated tests (which **clear the local test database**; use on a fresh copy only):

```bat
.venv\Scripts\python.exe -m pytest -q
```

**27 of 28 backend tests passed in the v6 build environment** (one synthetic cartoon-face test fails). Five new feature tests passed. Prior v4/v5 test figures are outdated. JSX syntax parsing passed; the complete Vite build was not possible without npm packages. In the previous release, including question-history aggregation, privacy, CSV safety, and deletion. Synthetic/blank-image and mocked-vector recognition tests do **not** verify actual webcam accuracy or person recognition on real faces. The React JSX passed syntax parsing; a full Vite build could **not** run in the packaging environment because npm registry packages were not available. After `npm ci`, validate with `npm run build` on Windows.

## API summary

- `POST /api/detect-person` — face presence only, with Haar fallback.
- `GET /api/recognition/status` — model readiness and enrolled count for current user.
- `POST /api/recognition/install` — fetch verified models in local demo mode.
- `POST /api/family-members/{id}/enroll?consent=true` — enroll consented photo; max five samples per person.
- `DELETE /api/family-members/{id}/enrollment` — delete face samples.
- `POST /api/recognize-person` — identify among currently enrolled people or return unknown.
- `POST /api/question` — return an answer grounded in saved records; log question and named object request when appropriate.
- `POST /api/object-lookup` — find a caregiver-saved object by name and log the explicit request (does not use the camera).
- `GET /api/caregiver/monitoring?days=30` — activity totals, recently asked objects, repeated objects, questions, notes, timeline, and follow-up suggestions.
- `GET /api/caregiver/monitoring.csv?days=30` — spreadsheet-safe object request export.
- `DELETE /api/caregiver/object-lookups` — remove object-request history for this account.
- `POST /api/caregiver/notes` — store voluntary caregiver notes.
- `DELETE /api/caregiver/notes/{id}` — remove a saved note.
- `POST /api/identity-reminder` — explicitly save an enrolled profile reminder after a possible match; not proof of a real encounter.
- `DELETE /api/caregiver/identity-reminders` — erase saved identity prompts via API.
- `GET /api/caregiver/analytics?days=30` — account-owned aggregated activity.
- `GET /api/caregiver/questions.csv?days=30` — download the current account's questions as CSV.
- `DELETE /api/caregiver/questions` — erase all logged questions for the account.

## Demo script (~3 minutes)

1. Show the home screen and one-tap patient actions.
2. Enroll a consenting volunteer (done *before* the pitch), recognize them via camera, and show a label and optional voice readout. An unknown face should **not** receive a guessed name.
3. Ask “Where are my keys?” and “Who is Anu?”; show the answer retrieved from saved data.
4. Open Caregiver Studio and highlight **Questions asked**, **Most repeated questions**, and **Needs caregiver input**; show charts with fake demo history.
5. Explain user-scoped storage and the difference between face detection and identity matching; end with future roadmap for accessibility and real-world testing.

## Privacy, limits and deployment

This is a **local hackathon demo**, not a clinical device, validated identity system, or emergency-alert service. **No medical diagnosis is generated**, and the app must not be used to make medical decisions. Identity recognition can be wrong. Only enroll people with informed permission. Uploaded enrollment vectors are stored in SQLite *unencrypted at rest*; scan images are not saved. The demo uses one signed-in account with access to both patient and caregiver views; **independent caregiver role authorization has not been implemented**. A production rollout requires role separation, encrypted at-rest storage, retention choices, consent audit, accuracy/fairness evaluations across diverse faces, HTTPS, and threat modeling. Do not put actual patient records in a public hackathon demonstration.

Models: OpenCV Zoo [YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) and [SFace](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface), with their own license notices. Model hashes checked as part of download.
