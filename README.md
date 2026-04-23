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

## Setup
1. Install SWI-Prolog.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python app.py
   ```

## Notes
This is a transparent rule-based demo. It flags **possible** fallacies and works best on short, explicit speech excerpts.
