import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from plan_checker.cli import main

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "samples")


class TestCli(unittest.TestCase):
    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_messy_sample_exits_2_and_covers_rules(self):
        code, out, _ = self.run_cli([os.path.join(SAMPLES, "plans_messy.json")])
        self.assertEqual(code, 2)
        for rule in ("PLAN001", "PLAN002", "PLAN003", "PLAN004"):
            self.assertIn(rule, out)

    def test_clean_sample_exits_0(self):
        code, out, _ = self.run_cli([os.path.join(SAMPLES, "plans_clean.json")])
        self.assertEqual(code, 0)
        self.assertIn("RESULT: clean", out)

    def test_bad_quota_unit_exits_2(self):
        doc = ('{"usage_plans": [{"ocid": "p", "entitlements": [{"name": "e", '
               '"quota": {"value": 5, "unit": "YEAR", "operation_on_breach": "REJECT"}}]}]}')
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write(doc)
            path = fh.name
        try:
            code, _, err = self.run_cli([path])
            self.assertEqual(code, 2)
            self.assertIn("unit must be one of", err)
        finally:
            os.unlink(path)

    def test_malformed_json_exits_2(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write("{nah")
            path = fh.name
        try:
            code, _, err = self.run_cli([path])
            self.assertEqual(code, 2)
            self.assertIn("not valid JSON", err)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
