from __future__ import annotations

import os
import tempfile
from pathlib import Path

from flask import Flask, render_template, request
from preprocess import speech_to_facts
from pyswip import Prolog

BASE_DIR = Path(__file__).resolve().parent
RULES_FILE = BASE_DIR / "fallacies.pl"

app = Flask(__name__)


def _prolog_path(path: Path) -> str:
    return path.resolve().as_posix()


def run_prolog_analysis(facts_text: str):
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".pl",
        prefix="speech_facts_",
        dir="/tmp",
        delete=False,
        encoding="utf-8",
    ) as temp_facts:
        temp_facts.write(facts_text)
        temp_facts_path = Path(temp_facts.name)

    prolog = Prolog()
    try:
        prolog.consult(_prolog_path(RULES_FILE))
        prolog.consult(_prolog_path(temp_facts_path))

        claims = []
        claim_lookup = {}
        for result in prolog.query("claim(ID), text(ID, Text), type(ID, Type), target(ID, Target)"):
            cid = str(result["ID"])
            row = {
                "id": cid,
                "text": str(result["Text"]),
                "type": str(result["Type"]),
                "target": str(result["Target"]),
            }
            claims.append(row)
            claim_lookup[cid] = row["text"]

        supports = []
        for result in prolog.query("supports(C1, C2, Reason)"):
            c1 = str(result["C1"])
            c2 = str(result["C2"])
            supports.append(
                {
                    "claim1": c1,
                    "claim2": c2,
                    "claim1_text": claim_lookup.get(c1, c1),
                    "claim2_text": claim_lookup.get(c2, c2),
                    "reason": str(result["Reason"]),
                }
            )

        fallacies = []
        seen = set()

        for result in prolog.query("fallacy(Type, C1, C2)"):
            row = (str(result["Type"]), str(result["C1"]), str(result["C2"]))
            if row not in seen:
                seen.add(row)
                fallacies.append(
                    {
                        "type": row[0],
                        "claim1_id": row[1],
                        "claim2_id": row[2],
                        "claim1_text": claim_lookup.get(row[1], row[1]),
                        "claim2_text": claim_lookup.get(row[2], row[2]),
                    }
                )

        for result in prolog.query("fallacy(Type, C1)"):
            row = (str(result["Type"]), str(result["C1"]), None)
            if row not in seen:
                seen.add(row)
                fallacies.append(
                    {
                        "type": row[0],
                        "claim1_id": row[1],
                        "claim2_id": None,
                        "claim1_text": claim_lookup.get(row[1], row[1]),
                        "claim2_text": None,
                    }
                )

        explanations = {}
        for result in prolog.query("explanation(Type, Message)"):
            explanations[str(result["Type"])] = str(result["Message"])

        return claims, supports, fallacies, explanations
    finally:
        try:
            temp_facts_path.unlink(missing_ok=True)
        except OSError:
            pass


@app.route("/health")
def health():
    return {"status": "ok"}, 200


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
            claims, supports, fallacies, explanations = run_prolog_analysis(facts)

    return render_template(
        "index.html",
        input_text=input_text,
        claims=claims,
        supports=supports,
        fallacies=fallacies,
        explanations=explanations,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
