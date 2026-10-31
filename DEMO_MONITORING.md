# Patient Activity Monitor — 2-minute hackathon walkthrough

1. Launch ReMind AI locally with `START_WINDOWS.cmd`, then click **Try interactive demo**.
2. In **Find my things**, tap **Pen**. The answer cites the caregiver-saved location: *desk organizer*. Tap **Wallet**. The app should say no saved location exists.
3. Return home and ask **Where is my pen?** and **Where are my glasses?**.
4. Enter **Caregiver Studio** and refresh **Patient activity monitor**. You should now see Pen and Wallet in Recent objects and pen in Most requested objects. Missing object locations includes Wallet.
5. Click **Questions** and **Objects** in the activity timeline. Check the timestamps, most requested objects, and daily activity.
6. Add a caregiver note: *Put the blue pen in the desk organizer*. Show it in the timeline and caregiver notes.
7. Explain how no background camera recordings or photographic object detections are claimed. A question about a pen means the patient **asked about a pen**, not that the model visually detected one.
8. Optionally show face-recognition if models and enrolled volunteer photos have been installed and tested before the demo. The **Save this profile reminder** action logs the user's deliberate choice, not proof of a real encounter.

**Privacy:** Use only fictional demonstration records. Exported CSV files and database copies must not be published when real personal details have been entered.

**Judge-facing description:** ReMind AI helps patients recover familiar information and gives caregivers context about which memories and items need updating. The dashboard summarizes logged app interactions, not medical status or cognitive performance.
