"""Reader/writer resource closure, including valid untrusted receipt metadata."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from evalenvelope import Error
from evalenvelope.cli import output, read


class OutputTests(unittest.TestCase):
    def test_real_cli_compact_receipt_state_cannot_export_unreadably(self):
        probe = Path(__file__).resolve().parents[1]/"docs/evidence/probe_output_cap.py"
        p = subprocess.run([sys.executable, "-I", str(probe)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
        result = json.loads(p.stdout)
        self.assertTrue(result["typed_refusal"])
        self.assertEqual(result["import_exit"], 2)
        self.assertTrue(result["destination_preserved"] and result["source_preserved"])

    def test_exact_utf8_file_limit_and_one_byte_over_preserve_file_and_stdout(self):
        cap = 4*1024*1024
        overhead = len((json.dumps({"x": ""}, indent=2, sort_keys=True)+"\n").encode("utf-8"))
        legal = {"x": "x"*(cap-overhead)}
        too_large = {"x": legal["x"]+"x"}
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/"limit.json"
            output(legal, p)
            self.assertEqual(p.stat().st_size, cap)
            self.assertEqual(read(p), legal)
            before = p.read_bytes()
            with self.assertRaisesRegex(Error, "JSON output exceeds"): output(too_large, p)
            self.assertEqual(p.read_bytes(), before)
            missing = Path(temp)/"no-created-parent"/"output.json"
            with self.assertRaises(Error): output(too_large, missing)
            self.assertFalse(missing.parent.exists())
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout), self.assertRaises(Error): output(too_large, None)
            self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__": unittest.main()
