# ReMindAI v7: test report

- Date: 2026-10-31
- Backend: **36 passed, 0 failed** (`python -m pytest -q`).
- Fixed the existing failing synthetic-face endpoint assertion by retaining a stable detector label (`haar` or `yunet`) while continuing to use Haar solely for face presence, not identity.
- Added new tests to ensure low-quality frames cannot receive a named result and conflicting multi-photo enrollment cannot produce a named result.
- Previously added tests cover model availability, consent enforcement, per-user data isolation, duplicate template handling, cross-profile ambiguity and unknown-person results.
- Local ONNX models: model status ready; single face found in a local smoke image; extracting and comparing the SAME image gave a match. This is a pipeline sanity check only, **not an independent identity accuracy evaluation**.
- Frontend: `App.jsx` parsed successfully using TypeScript's JSX parser. **Full Vite build not tested** here because the `node_modules` dependency folder is unavailable.
- Windows webcam/camera permissions and real-life different-person discrimination not tested in this environment. Do not guarantee correct detection/recognition for real patients.

Important: pytest fixtures drop and recreate tables in the configured database. Set `DATABASE_URL` to a disposable file before running pytest. Do NOT point tests at `backend/remind_ai.db`.
