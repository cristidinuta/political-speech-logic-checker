"""
Political Speech Logic Checker — Local Prolog Server
No API key required. Receives pre-classified claims+features from the UI,
runs SWI-Prolog rule reasoning, returns fallacy results.
"""

import os
import subprocess
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

FALLACY_LABELS = {
    "ad_hominem":           "Ad Hominem",
    "false_dilemma":        "False Dilemma",
    "slippery_slope":       "Slippery Slope",
    "hasty_generalization": "Hasty Generalization",
    "straw_man":            "Straw Man",
    "appeal_to_authority":  "Appeal to Authority",
    "red_herring":          "Red Herring",
}

FALLACY_COLORS = {
    "ad_hominem":           "#e74c3c",
    "false_dilemma":        "#e67e22",
    "slippery_slope":       "#f39c12",
    "hasty_generalization": "#8e44ad",
    "straw_man":            "#2980b9",
    "appeal_to_authority":  "#16a085",
    "red_herring":          "#c0392b",
}

PROLOG_KB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fallacies.pl")


def run_prolog_analysis(claims: list[dict], features: dict[int, list[str]]) -> dict:
    fact_lines = []
    for claim in claims:
        cid = claim["id"]
        safe_text = claim["text"].replace("'", "\\'")
        fact_lines.append(f"assert(claim({cid}, '{safe_text}')),")
        for feat in features.get(cid, []):
            fact_lines.append(f"assert(has_feature({cid}, {feat})),")

    prolog_script = f"""
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

    with tempfile.NamedTemporaryFile(mode="w", suffix=".pl", delete=False, prefix="checker_") as f:
        f.write(prolog_script)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["swipl", "-q", "-s", tmp_path],
            capture_output=True, text=True, timeout=30,
        )
        output = result.stdout
    finally:
        os.unlink(tmp_path)

    fallacy_map: dict[int, list[dict]] = {c["id"]: [] for c in claims}
    for line in output.splitlines():
        if line.startswith("FALLACY|"):
            parts = line.split("|", 3)
            if len(parts) == 4:
                _, cid_str, ftype, expl = parts
                cid = int(cid_str)
                fallacy_map[cid].append({
                    "type": ftype,
                    "label": FALLACY_LABELS.get(ftype, ftype),
                    "explanation": expl,
                    "color": FALLACY_COLORS.get(ftype, "#666"),
                })

    analyzed = []
    for claim in claims:
        cid = claim["id"]
        analyzed.append({
            "id": cid,
            "text": claim["text"],
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


@app.route("/reason", methods=["POST"])
def reason():
    data = request.get_json()
    claims = data.get("claims", [])
    features = {int(k): v for k, v in data.get("features", {}).items()}
    if not claims:
        return jsonify({"error": "No claims provided"}), 400
    try:
        return jsonify(run_prolog_analysis(claims, features))
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Prolog reasoning timed out"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("LogicWatch Prolog server → http://localhost:5000")
    print("No API key needed — AI runs in the browser UI.")
    app.run(debug=True, port=5000)
