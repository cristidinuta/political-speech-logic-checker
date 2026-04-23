# Fallacy Checker (Rule-Based, No AI API)

This project analyzes short speech excerpts using:
- Python for sentence/clause splitting and heuristic tagging
- SWI-Prolog for symbolic fallacy rules
- Flask for the web UI

## Detected fallacies
- ad hominem
- hasty generalization
- false dilemma
- slippery slope
- appeal to authority
- appeal to popularity

## Local setup
1. Install SWI-Prolog.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python app.py
   ```

## Render deployment
This app is easiest to deploy on Render as a **Docker web service** because it needs the OS-level package `swi-prolog`.

### Option A: use `render.yaml`
Push this folder to GitHub and create a new Blueprint on Render. Render will detect `render.yaml` and build from the included `Dockerfile`.

### Option B: create the service manually
- Service type: **Web Service**
- Runtime: **Docker**
- Dockerfile path: `./Dockerfile`

### Why Docker here?
The Python runtime on Render is great for pure Python apps, but this project also depends on SWI-Prolog. The included Dockerfile installs that dependency and starts the app with Gunicorn.

## Production notes
- The app writes per-request Prolog facts into `/tmp`, which is safe for Render's ephemeral filesystem.
- It no longer relies on a shared `speech_facts.pl` file, so concurrent requests won't overwrite each other.
- Gunicorn is configured conservatively with one worker because PySwip / SWI-Prolog integrations are safer with a simple process model.

## Notes
This is a transparent rule-based demo. It flags **possible** fallacies and works best on short, explicit speech excerpts.
