## 2026-10-30 — Pending Cline work completed
- Added signed-in caregiver inbox with grouped unknown person/object notifications, manual add-details forms, dismiss, and a navbar badge refreshed every 20 seconds.
- Wired missing-person inquiries from patient questions and automatically resolved known-name/object requests when records are created or edited.
- Added daily caregiver-assigned tasks, patient self-reports, caregiver verify/review actions, and achievement summaries.
- Added three-question daily recall check-in plus answer validation, repeat-answer protection, immediate feedback, and caregiver daily trends.
- Added synthetic demo tasks, an unresolved name inquiry, and historical quiz records for hackathon demonstration.
- Added 5 integration tests. See FEATURES_COMPLETED.md for limitations, database preservation, and setup notes.

# ReMind AI — v4 Patient Activity Monitor

## New in v4

- New caregiver **Patient activity monitor** above existing question analytics. Responsive pastel activity cards, recently asked questions, recently requested objects, top objects, missing saved locations, daily chart, and filterable timeline.
- **Object requests** are now logged when the patient explicitly asks a location question (e.g. “Where is my pen?”) or chooses an item in the Object Finder. Works even if an object has no saved location. Do not confuse object requests with visual object detections.
- **Object Finder** accepts custom names and quick chips (Pen, Glasses, Keys, Phone, Wallet, Cup). Item cards have a one-tap request action.
- **Caregiver notes** can be added and deleted, with timestamps.
- **Optional identity profile reminders** can be saved after a matched face is shown; these are user-triggered reminders and are not evidence of a real-world meeting.
- **Follow-up suggestions** for requests without saved answers/locations; per-day question/object activity; 7/30/90/all-time filters; CSV export and delete controls for object history.
- New SQLite tables `object_inquiries`, `caregiver_notes`, `identity_reminders` created automatically on startup. Records are scoped to the current signed-in account.
- **23 passing backend regression tests**; frontend JSX syntax parsed successfully with TypeScript. Full browser and production build remain to be verified on Windows after `npm ci`.

## Limitations

- No camera-based object identification of a pen. No continuous location surveillance. No medical analytics or diagnosis.
- Real webcam face identification still requires YuNet + SFace downloads and consented face enrollment. Those weights could not be bundled in this environment.
- This is a local single-account demo with patient and caregiver screens; independent caregiver-role access, database encryption, long-term consent records, and production monitoring controls are not yet implemented.

---

# What's changed in this version

**New analytics dashboard**

- QuestionEvent table to track question text, normalized repetition, topic, answered/not answered, voice/typed/quick input, and time. Existing SQLite installations gain this new table automatically.
- 7/30/90-day and all-time analytics endpoint; private per-account totals, top questions, category distribution, daily graph, recent-question list.
- Caregiver Studio redesigned with accessible visual summary cards, simple bar charts, CSV export, and clear-history action.
- Demo seeds a fabricated question history for judging without needing real patient data.

**Face detection & identity setup**

- Lower latency, lazily loaded YuNet model with synchronized access, and offline OpenCV Haar fallback.
- Identity feature boxes are clipped correctly for out-of-bounds results; YuNet uses a slightly more forgiving detector threshold.
- Automatic attempt to install the two verified OpenCV models in Windows setup; multiple official-source fallbacks and a dedicated retry command.
- Three-step recognition progress strip, explicit model-not-ready explanation, accessible error messages, optional read-aloud with language selection.
- Independent read-only backend model diagnostic script and `CHECK_FACE_SETUP_WINDOWS.cmd`.
- No face is given a name without a matching, enrolled, consenting profile.

**UX and reliability**

- Patient reassurance/onboarding panel, simpler wording, example-question chips, and smoother screen-to-screen workflows.
- Backend input length validation; questions are persisted only when the service returns an answer response.
- 18 backend regression tests pass (3 additional tests for analytics). Frontend JSX syntax checked, but complete `npm run build` is still required on a Windows machine with dependencies installed.

**Limitations**

- Models themselves are not bundled. Internet is required once for the official ONNX weights.
- No claim of validated real-world recognition accuracy; local build environment lacks physical webcam and real consented enrollment data.
- Caregiver analytics are descriptive usage counts, not cognitive/medical analysis. This is a demo, not a deployed clinical service.
