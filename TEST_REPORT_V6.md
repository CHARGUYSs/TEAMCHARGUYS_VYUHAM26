# ReMindAI v6 — test report

## Results

- Total backend tests: **28**
- Passed: **27**
- Failed: **1**
- New requested-feature tests: **5/5 passed**
- Source syntax: **3/3 JSX files parse successfully**, Python `compileall` passes.
- Full Vite build: **not verified** (npm packages were not available offline in this environment). Run `npm ci` then `npm run build` in `frontend` on Windows.

### Known failing test

`tests/test_app.py::test_face_endpoint_on_synthetic_face_and_boxes` expects the face detector to recognize a crude cartoon drawn using an ellipse, circles, and a rectangle. The face detector returned zero boxes. This existed independently of the five requested upgrades and is not evidence that all camera recognition succeeds or fails in real conditions; test with consenting volunteers using real camera images.

### Verified requested workflows

1. Date-based task creation, ascending task order, patient today/upcoming display API, and account isolation; future tasks cannot be completed or verified early or affect today's achievement rate.
2. Refreshing personalized quiz after new family/object records, preserving answered history, and stable GET reload.
3. Photos uploaded and privately retrieved; video accepted; MIME-type and size checks; unauthorized access/upload/delete denied; deletion removes private media.
4. Earliest timestamp calculated across scheduled events and reminders.
5. 3-stage non-clinical *data coverage* indicator computed using answered quizzes, separate days, and question activity, with explanatory limitations.

### Safest way to rerun tests

Tests rebuild the selected SQLite database. **Do not run pytest with your real `backend/remind_ai.db`.**

On Windows CMD in `backend`, create a throwaway DB variable for testing, for example:

```bat
set DATABASE_URL=sqlite:///./remind_test_disposable.db
.venv\Scripts\python.exe -m pytest -q
set DATABASE_URL=
```

`remind_test_disposable.db` will be cleared by the test fixtures, not your original database. Use made-up/synthetic data in demos; do not treat face recognition, memory statistics or task checks as medically validated.
