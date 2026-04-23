from flask import Flask, render_template, request
from preprocess import speech_to_facts
from pyswip import Prolog

app = Flask(__name__)

FACTS_FILE = "speech_facts.pl"
RULES_FILE = "fallacies.pl"


def run_prolog_analysis():
    """Load facts + rules and return claims, support links, fallacies, and explanations."""
    prolog = Prolog()
    prolog.consult(RULES_FILE)
    prolog.consult(FACTS_FILE)

    claims = []
    for result in prolog.query("claim(ID), text(ID, Text), type(ID, Type), target(ID, Target)"):
        claims.append({
            "id": str(result["ID"]),
            "text": str(result["Text"]),
            "type": str(result["Type"]),
            "target": str(result["Target"]),
        })

    supports = []
    for result in prolog.query("supports(C1, C2, Reason)"):
        supports.append({
            "claim1": str(result["C1"]),
            "claim2": str(result["C2"]),
            "reason": str(result["Reason"]),
        })

    fallacies = []
    seen = set()

    for result in prolog.query("fallacy(Type, C1, C2)"):
        row = (str(result["Type"]), str(result["C1"]), str(result["C2"]))
        if row not in seen:
            seen.add(row)
            fallacies.append({
                "type": row[0],
                "claim1": row[1],
                "claim2": row[2],
            })

    for result in prolog.query("fallacy(Type, C1)"):
        row = (str(result["Type"]), str(result["C1"]), None)
        if row not in seen:
            seen.add(row)
            fallacies.append({
                "type": row[0],
                "claim1": row[1],
                "claim2": None,
            })

    explanations = {}
    for result in prolog.query("explanation(Type, Message)"):
        explanations[str(result["Type"])] = str(result["Message"])

    return claims, supports, fallacies, explanations


@app.route("/", methods=["GET", "POST"])
def index():
    claims = []
    supports = []
    fallacies = []
    explanations = {}
    input_text = ""

    if request.method == "POST":
        input_text = request.form.get("speech", "").strip()
        if input_text:
            facts = speech_to_facts(input_text)
            with open(FACTS_FILE, "w", encoding="utf-8") as f:
                f.write(facts)
            claims, supports, fallacies, explanations = run_prolog_analysis()

    return render_template(
        "index.html",
        input_text=input_text,
        claims=claims,
        supports=supports,
        fallacies=fallacies,
        explanations=explanations,
    )


if __name__ == "__main__":
    app.run(debug=True)
