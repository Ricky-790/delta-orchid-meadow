import json
import sys
import unittest
from pathlib import Path

import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gatepass import build, load

ROOT = Path(__file__).resolve().parent.parent


class TestValidation(unittest.TestCase):
    def test_output_matches_schema(self):
        path = ROOT / "output" / "result.json"
        schema = load.load_json(ROOT / "data" / "output_schema.json")
        output = json.loads(path.read_text())
        jsonschema.validate(output, schema)

    def test_build_rejects_bad_evidence(self):
        quotes = load.load_interviews(ROOT / "data" / "interviews.json")
        draft = {
            "requirements": [
                {"text": "x", "source_persona": "dev", "status": "confirmed",
                 "evidence": ["dev#99"]},
                {"text": "y", "source_persona": "anjali", "status": "confirmed",
                 "evidence": ["anjali#0"]},
                {"text": "z", "source_persona": "dev", "status": "confirmed",
                 "evidence": ["dev#0"]},
            ],
            "conflicts": [], "constraints": [], "budget_inr": None,
            "budget_evidence": [], "plan": [], "open_questions": [],
        }
        output, rejected = build.build_output(draft, [], quotes, "note")
        self.assertEqual(rejected, 2)
        self.assertEqual(len(output["requirements"]), 1)
        self.assertEqual(output["requirements"][0]["id"], "R1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
