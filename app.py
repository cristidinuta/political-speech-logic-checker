"""
LogicWatch — Flask + SWI-Prolog, zero external API.
NLP done with pure Python regex/keyword pattern matching.
"""

import os, re, json, subprocess, tempfile
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

PROLOG_KB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fallacies.pl")

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
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])|(?<=\.)\s*(?=Furthermore|However|But|Also|Moreover|Additionally|Therefore|Thus|So,)', text)
    sentences = []
    for i, s in enumerate(parts, 1):
        s = s.strip()
        if len(s) > 15:
            sentences.append({"id": i, "text": s})
    return sentences

# ── Feature detectors — each returns True/False ────────────────────────────
def d(text, patterns):
    t = text.lower()
    return any(re.search(p, t) for p in patterns)

DETECTORS = {
    "attacks_person": lambda t: d(t, [
        r"\bhe (is|was|has been)\b", r"\bshe (is|was|has been)\b",
        r"\bmy opponent\b", r"\bcrook\b", r"\bliar\b", r"\bcorrupt\b",
        r"\barrested\b", r"\bcriminal\b", r"\bscandal\b", r"\bcheat\b",
        r"\bdishonest\b", r"\buntrustworthy\b", r"\bincompetent\b",
        r"\bembezzl\b", r"\bfraud\b", r"\bfailed (leader|politician)\b",
    ]),
    "ignores_argument": lambda t: d(t, [
        r"\bso (you|we) can'?t trust\b", r"\bso nothing (he|she|they) say\b",
        r"\bwhat (he|she|they) say(s)? (is|means) nothing\b",
        r"\bdisqualif\b", r"\bmakes? (him|her|them) unfit\b",
        r"\bshould not be believed\b", r"\bcan'?t be trusted\b",
    ]),
    "binary_choice": lambda t: d(t, [
        r"\beither\b.{0,60}\bor\b", r"\byou('re| are) (with|against) (us|me)\b",
        r"\bonly two (options|choices|paths|ways)\b",
        r"\bif not.{0,40}then\b", r"\bno (other|alternative) (choice|option|way)\b",
        r"\bit'?s (us or them|now or never|this or that)\b",
        r"\bif you (don'?t|won'?t).{0,40}then\b",
    ]),
    "acknowledges_alternatives": lambda t: d(t, [
        r"\bother option\b", r"\balternative\b", r"\banother (way|approach|path)\b",
        r"\bof course.{0,30}could also\b", r"\bone possibility\b",
    ]),
    "chain_of_consequences": lambda t: d(t, [
        r"\bif.{0,60}then.{0,60}(will|would|could)\b",
        r"\bleads? to\b", r"\bwill lead to\b", r"\bwill result in\b",
        r"\beventually\b.{0,40}\b(collapse|fail|destroy|end)\b",
        r"\bonce.{0,40}then\b", r"\bif we (allow|let|permit)\b",
        r"\bsoon.{0,60}(will|would)\b",
    ]),
    "extreme_endpoint": lambda t: d(t, [
        r"\bcollapse\b", r"\bdestroy(ed)?\b", r"\bend of\b", r"\bchaos\b",
        r"\bdisaster\b", r"\bcatastroph\b", r"\bdoom\b", r"\bruined?\b",
        r"\bwipe(d)? out\b", r"\bextreme\b", r"\btyranny\b", r"\bdictator\b",
        r"\bnever recover\b", r"\birreversible\b", r"\barrest(ed)?\b.{0,30}\bindependent\b",
    ]),
    "causal_evidence": lambda t: d(t, [
        r"\bstudie(s|d) show\b", r"\bdata (shows?|suggests?|indicates?)\b",
        r"\baccording to research\b", r"\bevidence (shows?|suggests?)\b",
        r"\bstatistic(ally|s)\b", r"\bproven\b", r"\bscientific(ally)?\b",
        r"\bpeer.reviewed\b",
    ]),
    "broad_generalization": lambda t: d(t, [
        r"\beveryone\b", r"\ball (of them|immigrants|politicians|liberals|conservatives)\b",
        r"\bnobody\b", r"\bno one\b", r"\balways\b", r"\bnever\b",
        r"\bevery single\b", r"\bwithout exception\b", r"\bthe (whole|entire) country\b",
        r"\ball (people|americans|voters)\b", r"\bany (true|real|honest)\b",
    ]),
    "limited_sample": lambda t: d(t, [
        r"\bone (example|case|instance|incident|time|person|city|town|state)\b",
        r"\bthis (one|single)\b", r"\bI (know|met|saw|spoke to) (a|one|someone)\b",
        r"\blast (month|week|year)\b.{0,30}\bproves?\b",
        r"\bone (bad|good)\b.{0,40}\b(proves?|shows?|means?)\b",
        r"\ba (recent|single) (incident|case|example)\b",
    ]),
    "misrepresents_opponent": lambda t: d(t, [
        r"\bmy opponent (wants?|believes?|thinks?|claims?|says?)\b",
        r"\bthey (want|believe|think|claim|say).{0,40}(obviously|clearly|basically|essentially)\b",
        r"\bwhich (obviously|clearly|basically) means\b",
        r"\bso (he|she|they) (want|believe|think)\b",
        r"\bin other words.{0,40}(he|she|they)\b",
        r"\bwhat (he|she|they) really (mean|want)\b",
    ]),
    "attacks_misrepresentation": lambda t: d(t, [
        r"\bwhich (obviously|clearly) means (he|she|they) want(s)? to\b",
        r"\bso (he|she|they) (want|support|believe).{0,40}(extreme|radical|destroy|eliminate|ban|end)\b",
        r"\bthat'?s (crazy|insane|extreme|radical|dangerous|absurd)\b",
        r"\b(ridiculous|absurd|extreme|dangerous) (position|idea|plan|proposal)\b",
    ]),
    "cites_authority": lambda t: d(t, [
        r"\baccording to\b", r"\b(expert|professor|doctor|scientist|economist|general|admiral)\b",
        r"\bstudies (show|say|prove)\b", r"\bresearch(ers)? (show|say|prove|found)\b",
        r"\b(harvard|yale|oxford|mit|stanford|cdc|who|fbi|cia)\b",
        r"\b(endorsed|supported|backed) by\b", r"\b(nobel|pulitzer)\b",
        r"\bcelebrity\b", r"\bfamous\b.{0,20}\b(said|says|believes)\b",
    ]),
    "irrelevant_authority": lambda t: d(t, [
        r"\bcelebrity\b", r"\bactor\b", r"\bsinger\b", r"\bathlete\b",
        r"\bspokesperson\b", r"\binfluencer\b",
        r"\b(endorsed|supported) (by|on) (tv|television|social media|instagram|twitter)\b",
        r"\bon (tv|television|the show|the program)\b",
    ]),
    "no_supporting_evidence": lambda t: (
        d(t, [r"\bsettles? the (debate|matter|question|issue)\b",
              r"\bthat'?s (all|enough|settled|final)\b",
              r"\bperiod\b", r"\bend of (story|discussion|debate)\b",
              r"\bno (further|more) (debate|discussion|question)\b",
              r"\bcase closed\b"])
        and not d(t, [r"\bdata\b", r"\bstudy\b", r"\bevidence\b",
                      r"\bstatistic\b", r"\bresearch\b", r"\bproof\b"])
    ),
    "topic_diversion": lambda t: d(t, [
        r"\bbut (what|look) about\b", r"\bwhat about\b",
        r"\binstead.{0,30}(focus|talk|think) about\b",
        r"\bthe real (issue|problem|question|concern) is\b",
        r"\bwhat voters (really|actually) care about\b",
        r"\blet'?s (talk|focus|think) about\b.{0,30}\binstead\b",
        r"\bmore importantly\b.{0,40}\b(look|consider|think)\b",
    ]),
    "ignores_main_issue": lambda t: d(t, [
        r"\bthat is why.{0,60}(can'?t|cannot|won'?t|should not)\b",
        r"\bso (we|you) (can'?t|cannot|won'?t|should not) (afford|consider|support|do)\b",
        r"\bchanges? the (subject|topic|conversation)\b",
        r"\bavoid(ing|s)? the (question|issue|point)\b",
    ]),
}

def detect_features(text):
    return [feat for feat, fn in DETECTORS.items() if fn(text)]

# ── Prolog runner ──────────────────────────────────────────────────────────
def run_prolog(claims, features):
    fact_lines = []
    for c in claims:
        cid = c["id"]
        safe = c["text"].replace("'", "\\'")
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
        f.write(script); tmp = f.name
    try:
        out = subprocess.run(["swipl","-q","-s",tmp], capture_output=True, text=True, timeout=30).stdout
    finally:
        os.unlink(tmp)

    fallacy_map = {c["id"]: [] for c in claims}
    for line in out.splitlines():
        if line.startswith("FALLACY|"):
            parts = line.split("|", 3)
            if len(parts) == 4:
                _, cid_s, ftype, expl = parts
                cid = int(cid_s)
                fallacy_map[cid].append({
                    "type": ftype,
                    "label": FALLACY_LABELS.get(ftype, ftype),
                    "explanation": expl,
                    "color": FALLACY_COLORS.get(ftype, "#666"),
                })

    analyzed = []
    for c in claims:
        cid = c["id"]
        analyzed.append({"id":cid,"text":c["text"],"features":features.get(cid,[]),"fallacies":fallacy_map[cid]})

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
    return jsonify({"status": "ok"})

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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
