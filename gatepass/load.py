import json
import re
from pathlib import Path

# A deflection refuses or redirects instead of answering. These patterns are
# name-agnostic so the tool works at another site. A quote matching any of
# them must not be cited as the sole evidence for a requirement.
DEFLECTION_PATTERNS = [
    r"\bask him\b",
    r"\bask her\b",
    r"\bfirst ask me\b",
    r"money is \w+'s desk",
    r"make it work and show me",
    r"whatever \w+ da says",
    r"what \w+ wants, \w+ decides",
    r"i open the gate, i close the gate",
    r"i (do not|don't) hand out",
    r"i do not have time for a long list",
    r"that is not something i decide",
    r"i would have to look at the file",
]


def load_json(path):
    return json.loads(Path(path).read_text())


def load_interviews(path):
    data = load_json(path)
    quotes = []
    for persona, info in data["personas"].items():
        for i, q in enumerate(info["quotes"]):
            text = q["text"]
            low = text.lower()
            quotes.append(
                {
                    "ref": f"{persona}#{i}",
                    "persona": persona,
                    "question": q["question"],
                    "text": text,
                    "is_deflection": any(
                        re.search(p, low) for p in DEFLECTION_PATTERNS
                    ),
                }
            )
    return quotes
