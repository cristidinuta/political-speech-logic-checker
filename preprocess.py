import re
from typing import List, Dict


CONNECTORS = [
    "because", "therefore", "thus", "hence", "so", "but", "however",
    "since", "although", "though", "while"
]

INSULT_WORDS = {
    "idiot", "fool", "corrupt", "clown", "stupid", "liar", "dishonest",
    "parasite", "criminal", "thief", "moron", "fraud", "crook"
}

BAD_ACT_WORDS = {
    "lied", "lie", "stole", "steal", "cheated", "cheat", "corrupt",
    "misled", "deceived", "deceive"
}

CATASTROPHE_WORDS = {
    "collapse", "destroy", "disaster", "ruin", "dead", "catastrophe",
    "chaos", "dictatorship", "tyranny", "end", "wipe out"
}

UNIVERSAL_WORDS = {
    "all", "always", "never", "nothing", "everyone", "nobody", "every", "none"
}

REJECTION_PATTERNS = [
    "cannot be trusted", "can't be trusted", "should not be trusted",
    "argument is wrong", "policy is worthless", "plan is worthless",
    "nothing he says is true", "nothing she says is true", "nothing they say is true",
    "everything he says is false", "everything she says is false", "everything they say is false",
    "should be rejected", "must be rejected"
]

CONCLUSION_CUES = ["therefore", "thus", "hence", "so"]


def escape_prolog_string(text: str) -> str:
    return text.replace("\\", "\\\\").replace("'", "\\'")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def split_into_sentences(text: str) -> List[str]:
    text = normalize_whitespace(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def split_atomic_clauses(sentence: str) -> List[str]:
    sentence = sentence.strip()
    lowered = sentence.lower()

    if "either" in lowered and re.search(r"\bor\b", lowered):
        return [sentence]

    # Keep simple if-then clauses together because they often encode the full fallacy.
    if lowered.startswith("if "):
        return [sentence]

    pattern = r"\b(?:because|therefore|thus|hence|however|but|although|though|while)\b"
    parts = re.split(pattern, sentence, flags=re.IGNORECASE)
    cleaned = [p.strip(" ,;:.!?") for p in parts if p.strip(" ,;:.!?")]

    # Second pass for 'and' / 'so' only when clauses are long enough.
    final_parts: List[str] = []
    for part in cleaned:
        subparts = re.split(r"\b(?:and|so)\b", part, flags=re.IGNORECASE)
        stripped = [s.strip(" ,;:.!?") for s in subparts if len(s.strip(" ,;:.!?")) > 3]
        final_parts.extend(stripped if stripped else [part])

    return final_parts if final_parts else [sentence]


def extract_target(clause: str) -> str:
    text = clause.lower()
    for token in ["opponent", "minister", "candidate", "president", "government", "they", "he", "she", "them", "him", "her"]:
        if re.search(rf"\b{re.escape(token)}\b", text):
            return token
    return "unknown"


def has_any_word(text: str, words) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


def classify_clause(clause: str) -> str:
    text = clause.lower().strip()

    if "either" in text and re.search(r"\bor\b", text):
        return "either_or"

    if text.startswith("if ") and has_any_word(text, CATASTROPHE_WORDS):
        return "conditional_catastrophe"

    if any(pattern in text for pattern in REJECTION_PATTERNS):
        return "broad_rejection"

    if has_any_word(text, BAD_ACT_WORDS):
        return "single_bad_act"

    if has_any_word(text, INSULT_WORDS):
        return "attack_target"

    if has_any_word(text, UNIVERSAL_WORDS):
        return "universal_claim"

    if has_any_word(text, CATASTROPHE_WORDS):
        return "catastrophe_claim"

    if re.search(r"\b(expert|scientist|economist|judge|general)\b", text) and re.search(r"\bsaid|says|agree|agrees|support|supports\b", text):
        return "authority_claim"

    if re.search(r"\b(many|most|millions|everyone|the people)\b", text):
        return "popularity_claim"

    return "claim"


def relation_label(prev_text: str, next_text: str) -> str:
    combined = f"{prev_text.lower()} {next_text.lower()}"
    if any(cue in combined for cue in CONCLUSION_CUES):
        return "explicit_conclusion"
    return "adjacent_inference"


def should_link(c1: Dict, c2: Dict) -> bool:
    t1, t2 = c1["type"], c2["type"]
    same_target = c1["target"] == c2["target"] and c1["target"] != "unknown"

    if t1 in {"single_bad_act", "attack_target"} and t2 in {"broad_rejection", "universal_claim"}:
        return same_target or t2 == "universal_claim"

    if t1 == "conditional_catastrophe" and t2 in {"catastrophe_claim", "claim"}:
        return True

    if t1 == "authority_claim" and t2 in {"claim", "broad_rejection", "universal_claim"}:
        return True

    if t1 == "popularity_claim" and t2 in {"claim", "broad_rejection", "universal_claim"}:
        return True

    return False


def speech_to_facts(text: str) -> str:
    sentences = split_into_sentences(text)
    facts: List[str] = []
    claims: List[Dict] = []
    claim_counter = 1

    for sentence in sentences:
        clauses = split_atomic_clauses(sentence)
        for clause in clauses:
            cid = f"c{claim_counter}"
            claim_type = classify_clause(clause)
            target = extract_target(clause)
            escaped_clause = escape_prolog_string(clause)

            facts.append(f"claim({cid}).")
            facts.append(f"text({cid}, '{escaped_clause}').")
            facts.append(f"type({cid}, {claim_type}).")
            facts.append(f"target({cid}, {target}).")

            claims.append({
                "id": cid,
                "text": clause,
                "type": claim_type,
                "target": target,
            })
            claim_counter += 1

    for i in range(len(claims) - 1):
        c1, c2 = claims[i], claims[i + 1]
        if should_link(c1, c2):
            reason = relation_label(c1["text"], c2["text"])
            facts.append(f"supports({c1['id']}, {c2['id']}, {reason}).")

    return "\n".join(facts) + "\n"
