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
This app is set up for a Docker web service on Render because it needs the OS-level package `swi-prolog`.

### Deploy
- Push this folder to GitHub.
- Create a new **Web Service** on Render.
- Choose **Docker** runtime.
- Render will build from the included `Dockerfile`.

## Notes
- Uses one Gunicorn worker for safer PySwip/SWI-Prolog behavior.
- Writes generated Prolog facts to `/tmp` per request.
- Includes `/health` for a simple health check.
- Displays full claim text in the UI, not just IDs.
