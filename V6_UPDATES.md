# ReMind AI v6 — Completed requested changes

## What changed

1. **Friendly question refresh.** On the patient Home page, under *A few friendly questions*, select **New questions**. This calls `POST /api/daily-quiz/refresh`, which rereads the account's approved family profiles and saved object locations and uses them to generate fresh questions. A changed relationship/location also permits an updated question. It never substitutes a made-up correct answer. Previously answered questions remain saved for 7/30/90-day statistics. Only the three most recent questions appear; if the data has no fresh combinations, the app says so instead of falsely claiming to have generated something new. The general *Refresh* button reloads the existing questions and tasks.

2. **Daily task date and order.** Caregiver Studio → *Assign a dated task* has a date picker. *Assigned tasks* displays all dates from earliest to latest (and uses creation order for same-day ties). The patient Home page shows **today and the next 14 days**, in ascending date order. Future tasks are clearly labelled *Upcoming* and **cannot** be marked done until their scheduled day. Caregiver verification/review continues to work as before. The existing demo has a shared patient/caregiver login, not separate role-restricted accounts.

3. **Memory library photos and videos.** Caregiver Studio → *Memory library* now accepts multiple photos/videos on creation, or as an attachment to an existing memory. Both caregiver and patient can view uploads in the memory library. Files are **not** publicly hosted under `frontend/public`; authenticated media endpoints check the signed-in account. Images: JPG, PNG, WebP (max 8 MB each). Video: MP4, WebM (max 40 MB each). The browser opens videos only when requested. Caregivers can delete an uploaded file. Deleting a memory also deletes its uploaded media. All uploads persist under `backend/uploads/memory/` in that same copy of the project and are **not** embedded in SQLite. **Back up both your `backend/remind_ai.db` and the `backend/uploads/` folder.** Never commit personal media or real patient DBs to a public repo. This is not encrypted storage.

4. **Upcoming activity + reminder order.** The Home page's *Coming up next* now compares both future schedule entries and reminders and displays the earliest time. The next items and the Caregiver Studio / *My day* agenda are sorted together in ascending timestamp order. Previously, Home compared schedule to schedule and reminders separately, which could show the wrong next event.

5. **Memory tracking phase (not disease stage).** The caregiver check-in card shows *Tracking Phase 1 / 2 / 3* based on the number of answered recall questions, different assessment days, and patient questions asked within the selected 30-day window. Rules: Phase 1 if fewer than 3 answered checks OR fewer than 3 patient questions; Phase 2 if fewer than 12 answered checks, fewer than 3 distinct assessment days, OR fewer than 8 patient questions; otherwise Phase 3. Higher phases **only mean more observations have been collected**. Correct answers and percentages are displayed separately; these figures do **not** diagnose dementia/Alzheimer's, measure cognitive impairment, or justify changes to medication/care.

## Run in Windows / VS Code

1. Extract the **complete** v6 ZIP into its own folder. Do not run it inside the ZIP.
2. To retain existing records, copy the existing `backend/remind_ai.db` and (if used) `backend/uploads/` into the new copy **while the server is stopped**. The complete ZIP also includes the original v5 database file; copying your newer live database is only necessary if it changed since you uploaded v5.
3. Run `SETUP_WINDOWS.cmd` for the first-time Python/Node installation, then `START_WINDOWS.cmd`.
4. Visit `http://127.0.0.1:5173` (backend API at `http://127.0.0.1:8000`).
5. Test: add a new family member or object in Caregiver Studio, go Home → **New questions**; assign tasks for different days; create a memory with a real JPEG and a browser-compatible MP4, and confirm the earliest reminder is selected.

## Verification and limits

- **Five new tests passed**: task order/scheduling, fresh grounded quiz, file permissions/validation and delete, combined upcoming ordering, and phase thresholds.
- **Backend suite:** 27 passed, 1 failed (pre-existing synthetic/cartoon-face detection assertion; it does not mean all real face detection fails).
- **Frontend:** App.jsx, CareFeatures.jsx, and MemoryMedia.jsx passed Babel JSX syntax parsing. A full Vite build was **not** possible in this build environment because npm packages were unavailable in the cache; run `npm ci && npm run build` in the `frontend` directory on your Windows machine.
- Video playback depends on the browser's codec support (H.264 MP4/WebM typically works). Recording video from the camera and face recognition of media library videos are **not** part of this feature.
- The application is a hackathon demo. There is no independent patient/caregiver authorization, background reminders, or validated medical risk prediction. Use synthetic data in presentations. Do not depend on it for safety-critical decisions.

## API additions

- `GET /api/daily-tasks?upcoming_days=14`: patient tasks from today through future 14 days.
- `GET /api/caregiver/daily-tasks`: caregiver assigned tasks sorted by date ascending.
- `POST /api/caregiver/daily-tasks`: body includes `task_date: "YYYY-MM-DD"`.
- `POST /api/daily-quiz/refresh`: create new grounded question batch; returns `new_count`.
- `POST /api/memories/{memory_id}/media`: authenticated `multipart/form-data` file upload.
- `GET /api/memories/media/{media_id}`: authenticated private file streaming.
- `DELETE /api/memories/media/{media_id}`: authenticated file removal.
- `GET /api/home`: includes `next_upcoming` and `upcoming_items` combined chronological data.
- `GET /api/caregiver/quiz-trends`: adds `tracking_phase`, `tracking_phase_number`, `phase_explanation`, `assessment_days`, and `questions_asked`.
