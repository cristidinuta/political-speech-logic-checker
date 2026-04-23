"""
LogicWatch — Flask + SWI-Prolog, zero external API.
NLP via Python regex + Prolog DCG rule reasoning.
"""

import os, re, subprocess, tempfile, shutil
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

PROLOG_KB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fallacies.pl")

# Find swipl at startup — check common locations
SWIPL = shutil.which("swipl") or "/usr/bin/swipl"

FALLACY_LABELS = {
    "ad_hominem":"Ad Hominem","false_dilemma":"False Dilemma",
    "slippery_slope":"Slippery Slope","hasty_generalization":"Hasty Generalization",
    "straw_man":"Straw Man","appeal_to_authority":"Appeal to Authority",
    "red_herring":"Red Herring",
}
FALLACY_COLORS = {
    "ad_hominem":"#e74c3c","false_dilemma":"#e67e22","slippery_slope":"#f39c12",
    "hasty_generalization":"#8e44ad","straw_man":"#2980b9",
    "appeal_to_authority":"#16a085","red_herring":"#c0392b",
}

# ── Sentence splitter ──────────────────────────────────────────────────────
def split_sentences(text):
    text = re.sub(r'\s+', ' ', text.strip())
    parts = re.split(
        r'(?<=[.!?])\s+(?=[A-Z"])'
        r'|(?<=\.)\s*(?=Furthermore|However|But |Also,|Moreover|Additionally|Therefore|Thus,|So,)',
        text
    )
    sentences = []
    for i, s in enumerate(parts, 1):
        s = s.strip()
        if len(s) > 15:
            sentences.append({"id": i, "text": s})
    return sentences

# ── Feature detectors ──────────────────────────────────────────────────────
def m(text, patterns):
    t = text.lower()
    return any(re.search(p, t) for p in patterns)

DETECTORS = {
    "attacks_person": lambda t: m(t, [
        r"\bmy opponent\b", r"\bembezzl\b", r"\barrested\b", r"\bcriminal\b",
        r"\bcorrupt\b", r"\bliar\b", r"\bcrook\b", r"\bdishonest\b",
        r"\bscandal\b", r"\bcheat\b", r"\buntrustworthy\b", r"\bincompetent\b",
        r"\bfraud\b",
    ]),
    "ignores_argument": lambda t: m(t, [
        r"\bso nothing (he|she|they) say\b",
        r"\bnothing (he|she|they) say(s)?\b.{0,40}\bcan be trusted\b",
        r"\bso (you|we) can'?t trust\b",
        r"\bcannot be trusted\b", r"\bcan'?t be trusted\b",
        r"\bmakes? (him|her|them) unfit\b", r"\bdisqualif\b",
    ]),
    "binary_choice": lambda t: m(t, [
        r"\beither\b.{0,80}\bor\b",
        r"\byou('re| are) (with|against) (us|me)\b",
        r"\bonly two (options|choices|paths|ways)\b",
        r"\bno (other|alternative) (choice|option|way)\b",
        r"\bif you (don'?t|won'?t).{0,60}then\b",
        r"\bif (we|they) don'?t.{0,60}(will|must|shall)\b",
    ]),
    "acknowledges_alternatives": lambda t: m(t, [
        r"\bother option\b", r"\balternative\b",
        r"\banother (way|approach|path)\b", r"\bone possibility\b", r"\bcould also\b",
    ]),
    "chain_of_consequences": lambda t: m(t, [
        r"\bif.{0,80}(will|would|could)\b",
        r"\bleads? to\b", r"\bwill lead to\b", r"\bwill result in\b",
        r"\bonce.{0,60}(will|then)\b",
        r"\bif we (allow|let|permit|accept|give)\b",
        r"\bsoon.{0,80}(will|would|collapses?|explodes?)\b",
        r"\blet in.{0,60}(soon|and then|eventually)\b",
        r"\bwithin (five|ten|two|three|a few) (years?|months?|decades?)\b",
    ]),
    "extreme_endpoint": lambda t: m(t, [
        r"\bcollapse[sd]?\b", r"\bdestroy(ed|s)?\b", r"\bchaos\b",
        r"\bdisaster\b", r"\bcatastroph\b", r"\bdoom\b", r"\bruined?\b",
        r"\btyranny\b", r"\bdictator\b", r"\bnever recover\b",
        r"\birreversible\b", r"\bexplodes?\b", r"\bcrisis\b",
        r"\bfull (government|state) control\b",
        r"\brecord (high|low)\b", r"\bflee\b", r"\bcollaps\b",
        r"\bunemployment will\b", r"\beconomy will\b",
    ]),
    "causal_evidence": lambda t: m(t, [
        r"\bstudies? show\b", r"\bdata (shows?|suggests?|indicates?)\b",
        r"\baccording to research\b", r"\bevidence (shows?|suggests?)\b",
        r"\bstatistic(ally|s)\b", r"\bscientific(ally)?\b",
        r"\bpeer.reviewed\b", r"\bclinical trial\b",
    ]),
    "broad_generalization": lambda t: m(t, [
        r"\beveryone\b", r"\bnobody\b", r"\bno one\b",
        r"\balways\b", r"\bnever\b", r"\bevery single\b",
        r"\bwithout exception\b", r"\bthe (whole|entire) (country|nation|world)\b",
        r"\ball (immigrants|politicians|liberals|conservatives|people|americans)\b",
        r"\banyone who\b", r"\bwhoever\b",
    ]),
    "limited_sample": lambda t: m(t, [
        r"\bone (example|case|instance|incident|person|city|town|state|worker|economist)\b",
        r"\ba (single|celebrity|famous)\b.{0,30}\b(doctor|expert|economist|scientist)\b",
        r"\bone (bad|good)\b.{0,40}\b(proves?|shows?|means?)\b",
        r"\bone undocumented\b", r"\bwe let in one\b",
        r"\blast (month|week|year)\b.{0,40}\bproves?\b",
    ]),
    "misrepresents_opponent": lambda t: m(t, [
        r"\bmy opponent (says?|wants?|believes?|thinks?|claims?)\b",
        r"\bwhich (obviously|clearly|basically|essentially) means\b",
        r"\bso (he|she|they) (want|believe|think|support)\b",
        r"\bwhat (he|she|they) really (mean|want|believe)\b",
        r"\bin other words.{0,40}(he|she|they)\b",
        r"\bthat means (he|she|they)\b",
    ]),
    "attacks_misrepresentation": lambda t: m(t, [
        r"\b(obviously|clearly) means (he|she|they) want(s)? to\b",
        r"\bdeport every (single)?\b",
        r"\bwants? to (destroy|eliminate|ban|end|abolish)\b",
        r"\b(extreme|radical|dangerous|absurd|ridiculous) (position|idea|plan|proposal|view)\b",
        r"\bso (he|she|they).{0,40}(destroy|eliminate|deport|abolish)\b",
    ]),
    "cites_authority": lambda t: m(t, [
        r"\baccording to\b",
        r"\b(expert|professor|doctor|scientist|economist|general|admiral)\b",
        r"\bstudies? (show|say|prove|found)\b",
        r"\b(harvard|yale|oxford|mit|stanford|cdc|who)\b",
        r"\b(endorsed|supported|backed) by\b",
        r"\bcelebrity\b", r"\bfamous (doctor|expert|scientist)\b",
        r"\b(nobel|pulitzer)\b",
        r"\bon (tv|television)\b.{0,40}\b(said|says|endorsed|supported)\b",
    ]),
    "irrelevant_authority": lambda t: m(t, [
        r"\bcelebrity\b", r"\bactor\b", r"\bsinger\b", r"\bathlete\b",
        r"\bon (tv|television)\b", r"\binfluencer\b", r"\bspokesperson\b",
    ]),
    "no_supporting_evidence": lambda t: (
        m(t, [
            r"\bsettles? the (debate|matter|question|issue)\b",
            r"\bthe science is settled\b",
            r"\bthat'?s (all|enough|settled|final)\b",
            r"\bcase closed\b",
            r"\bend of (story|discussion|debate)\b",
        ])
        and not m(t, [r"\bdata\b", r"\bstudy\b", r"\bevidence\b",
                      r"\bstatistic\b", r"\bresearch\b"])
    ),
    "topic_diversion": lambda t: m(t, [
        r"\bbut what about\b", r"\bwhat about\b",
        r"\bthe real (issue|problem|question|concern) is\b",
        r"\bwhat voters (really|actually) care about\b",
        r"\blook at (how|what|the)\b",
        r"\binstead (let'?s|we should) (talk|focus|think) about\b",
        r"\bmore importantly\b",
    ]),
    "ignores_main_issue": lambda t: m(t, [
        r"\bthat is why.{0,80}(can'?t|cannot|won'?t|should not|could not)\b",
        r"\bso (we|you) (can'?t|cannot|won'?t|should not) (afford|consider|support|do|allow)\b",
        r"\bthat'?s why.{0,80}(can'?t|cannot|won'?t|should not)\b",
        r"\b(pothole|traffic|sports)\b",
    ]),
}

def detect_features(text):
    return [feat for feat, fn in DETECTORS.items() if fn(text)]


# ── Prolog runner ──────────────────────────────────────────────────────────
def run_prolog(claims, features):
    fact_lines = []
    for c in claims:
        cid = c["id"]
        safe = c["text"].replace("\\", "\\\\").replace("'", "\\'")
        fact_lines.append(f"assert(claim({cid}, '{safe}')),")
        for feat in features.get(cid, []):
            fact_lines.append(f"assert(has_feature({cid}, {feat})),")

    script = f"""
:- use_module(library(lists)).
:- ['{PROLOG_KB_PATH}'].
:- {" ".join(fact_lines)}
:- findall(
       claim_result(Id, Text, FList),
       (claim(Id, Text), findall(f(FType, Expl), fallacy(Id, FType, Expl), FList)),
       Results
   ),
   forall(
       member(claim_result(Id, Text, FList), Results),
       (
           format("CLAIM|~w|~w~n", [Id, Text]),
           forall(
               member(f(FType, Expl), FList),
               format("FALLACY|~w|~w|~w~n", [Id, FType, Expl])
           )
       )
   ),
   halt.
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pl", delete=False, prefix="lw_") as f:
        f.write(script)
        tmp = f.name

    try:
        result = subprocess.run(
            [SWIPL, "-q", "-s", tmp],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0 and result.stderr:
            app.logger.error(f"Prolog stderr: {result.stderr[:500]}")
        out = result.stdout
    finally:
        os.unlink(tmp)

    fallacy_map = {c["id"]: [] for c in claims}
    seen = {}
    for line in out.splitlines():
        if line.startswith("FALLACY|"):
            parts = line.split("|", 3)
            if len(parts) == 4:
                _, cid_s, ftype, expl = parts
                cid = int(cid_s)
                key = (cid, ftype)
                if key not in seen:
                    seen[key] = True
                    fallacy_map[cid].append({
                        "type": ftype,
                        "label": FALLACY_LABELS.get(ftype, ftype),
                        "explanation": expl,
                        "color": FALLACY_COLORS.get(ftype, "#666"),
                    })

    analyzed = []
    for c in claims:
        cid = c["id"]
        analyzed.append({
            "id": cid, "text": c["text"],
            "features": features.get(cid, []),
            "fallacies": fallacy_map[cid],
        })

    fallacy_counts = {}
    for c in analyzed:
        for f in c["fallacies"]:
            fallacy_counts[f["label"]] = fallacy_counts.get(f["label"], 0) + 1

    return {
        "claims": analyzed,
        "summary": {
            "total_claims": len(claims),
            "claims_with_fallacies": sum(1 for c in analyzed if c["fallacies"]),
            "total_fallacies": sum(len(c["fallacies"]) for c in analyzed),
            "fallacy_counts": fallacy_counts,
        },
    }


# ── Routes ─────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/health")
def health():
    return jsonify({"status": "ok", "swipl": SWIPL})

@app.route("/debug", methods=["POST"])
def debug():
    """Returns raw features detected per sentence — useful for testing."""
    data = request.get_json()
    speech = (data.get("speech") or "").strip()
    if not speech:
        return jsonify({"error": "No speech provided"}), 400
    claims = split_sentences(speech)
    features = {c["id"]: detect_features(c["text"]) for c in claims}
    return jsonify({
        "swipl_path": SWIPL,
        "claims": [{"id": c["id"], "text": c["text"], "features": features[c["id"]]} for c in claims]
    })

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    speech = (data.get("speech") or "").strip()
    if not speech:
        return jsonify({"error": "No speech provided"}), 400
    try:
        claims = split_sentences(speech)
        if not claims:
            return jsonify({"error": "Could not extract any sentences"}), 400
        features = {c["id"]: detect_features(c["text"]) for c in claims}
        return jsonify(run_prolog(claims, features))
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Prolog reasoning timed out"}), 500
    except FileNotFoundError:
        return jsonify({"error": f"SWI-Prolog not found at '{SWIPL}'. Check Dockerfile."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"swipl found at: {SWIPL}")
    app.run(debug=False, host="0.0.0.0", port=port)
