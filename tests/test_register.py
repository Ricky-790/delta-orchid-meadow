import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gatepass import register

CMAP = {
    "sl": "sl", "date": "date", "vehicle": "vehicle", "in_time": "in_time",
    "out_time": "out_time", "type": "type", "invoice_no": "invoice_no",
    "chit_no": "chit_no", "guard": "guard",
    "type_values": {"invoice": "invoice", "chit": "chit"},
}

ROWS = [
    {"sl": 1, "date": "2026-10-01", "vehicle": "A 1", "in_time": "10:00",
     "out_time": "10:30", "type": "invoice", "invoice_no": "I1", "chit_no": None,
     "guard": "Bablu"},
    {"sl": 2, "date": "2026-10-02", "vehicle": "B 2", "in_time": "22:00",
     "out_time": "22:20", "type": "chit", "invoice_no": "I1", "chit_no": "C1",
     "guard": "Montu"},
    {"sl": 3, "date": "2026-10-03", "vehicle": "C 3", "in_time": "21:00",
     "out_time": "21:10", "type": "chit", "invoice_no": None, "chit_no": "C2",
     "guard": "Bablu"},
]

REG = {"source": "test register", "columns": list(ROWS[0].keys()), "rows": ROWS}


class TestRegister(unittest.TestCase):
    def setUp(self):
        self.findings = register.analyse(REG, CMAP, 20)

    def test_split(self):
        match = [f for f in self.findings if "3 movements" in f][0]
        self.assertIn("1 on invoices", match)
        self.assertIn("2 on handwritten chits", match)

    def test_night_and_guard(self):
        match = [f for f in self.findings if "at or after 20:00" in f][0]
        self.assertIn("1 by Montu", match)
        self.assertIn("1 by Bablu", match)

    def test_duplicate_invoice(self):
        match = [f for f in self.findings if "I1 appears 2 times" in f][0]
        self.assertIn("row 1", match)
        self.assertIn("row 2", match)

    def test_chit_with_invoice(self):
        match = [f for f in self.findings if "carry an invoice number" in f][0]
        self.assertTrue(match.startswith("1 of 2"))

    def test_unique_vehicles(self):
        self.assertTrue(any("3 of 3" in f for f in self.findings))

    def test_missing_value_column(self):
        self.assertTrue(any("no value, weight" in f for f in self.findings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
