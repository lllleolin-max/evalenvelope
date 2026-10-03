"""Actual registered-console byte closure, including Windows newline transport."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile
import unittest
from evalenvelope import Error, parse_manifest, empty_state, parse_state
from evalenvelope.cli import output

CAP = 4*1024*1024


def fixture(target):
    manifest = {"version": 1, "kind": "independent_boxes",
                "identity": {"manifest": "stdout-tests", "old_model": "old", "new_model": "new", "scorer": "s"},
                "strata": {"s": "1"}, "items": [{"id": "i", "stratum": "s",
                "old": {"low": "0", "high": "0", "cost": "1"},
                "new": {"low": "0", "high": "0", "cost": "1"}}]}
    m = parse_manifest(manifest); state = empty_state(m).data()
    state["receipts"] = [{"plan_digest": "a"*64, "prior_state_digest": "b"*64, "event_ids": ["r"]} for _ in range(999)]
    def formatted(value): return (json.dumps(value, indent=2, sort_keys=True)+"\n").encode("utf-8")
    q, rem = divmod(target-len(formatted(state)), 999)
    for r in state["receipts"]: r["event_ids"] = ["r"*(q+1)]
    state["receipts"][-1]["event_ids"][0] += "r"*rem
    payload = formatted(state)
    assert len(payload) == target
    compact = json.dumps(state, separators=(",", ":")).encode("utf-8")
    assert len(compact) < CAP
    parse_state(m, state)
    incoming = {"version": 1, "kind": "actual_observations", "identity": dict(m.identity),
                "manifest_digest": m.fingerprint, "observations": []}
    return manifest, compact, incoming, payload


class StdoutTests(unittest.TestCase):
    def test_registered_console_native_and_utf0_utf1_actual_byte_boundaries(self):
        cli = Path(sysconfig.get_path("scripts"))/("evalenvelope.exe" if os.name == "nt" else "evalenvelope")
        self.assertTrue(cli.is_file(), "install an ordinary wheel before testing")
        child_env = {k:v for k,v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME", "PYTHONUTF8", "PYTHONIOENCODING")}
        process_setting = sys.get_int_max_str_digits()
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            for mode in (None, "0", "1"):
                env = dict(child_env)
                if mode is not None: env["PYTHONUTF8"] = mode
                for size in (CAP-128, CAP, CAP+1):
                    with self.subTest(utf8=mode, formatted_bytes=size, platform=sys.platform):
                        manifest, source, incoming, expected = fixture(size)
                        mf, sf, incoming_file = d/"manifest.json", d/"state.json", d/"actual.json"
                        mf.write_text(json.dumps(manifest), encoding="utf-8"); sf.write_bytes(source)
                        incoming_file.write_text(json.dumps(incoming), encoding="utf-8")
                        args = [str(cli), "import", "--manifest", str(mf), "--state", str(sf), "--observations", str(incoming_file)]
                        p = subprocess.run(args, env=env, capture_output=True)
                        self.assertEqual(sf.read_bytes(), source)
                        if size <= CAP:
                            self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8"))
                            self.assertEqual(p.stdout, expected)
                            self.assertEqual(len(p.stdout), size)
                            self.assertNotIn(b"\r\n", p.stdout)
                            captured = d/"captured.json"; captured.write_bytes(p.stdout)
                            check = subprocess.run([str(cli), "analyze", "--manifest", str(mf), "--state", str(captured)], env=env, capture_output=True)
                            self.assertEqual(check.returncode, 0, check.stderr.decode("utf-8"))
                        else:
                            self.assertEqual(p.returncode, 2)
                            self.assertEqual(p.stdout, b"")
                            self.assertIn("JSON output exceeds", json.loads(p.stderr)["error"])
                            missing = d/"absent-parent"/"output.json"
                            p = subprocess.run([*args, "--output", str(missing)], env=env, capture_output=True)
                            self.assertEqual(p.returncode, 2); self.assertEqual(p.stdout, b"")
                            self.assertFalse(missing.parent.exists())
                            preserved = d/"preserved.json"; preserved.write_bytes(b"preserved-existing-output")
                            p = subprocess.run([*args, "--output", str(preserved)], env=env, capture_output=True)
                            self.assertEqual(p.returncode, 2); self.assertEqual(p.stdout, b"")
                            self.assertEqual(preserved.read_bytes(), b"preserved-existing-output")
                            self.assertEqual(sf.read_bytes(), source)
        self.assertEqual(sys.get_int_max_str_digits(), process_setting)

    def test_binary_output_bypasses_text_newline_and_encoding_without_reconfigure(self):
        raw = io.BytesIO(); wrapper = io.TextIOWrapper(raw, encoding="cp1252", newline="\r\n")
        value = {"receipt_metadata": "unicode 中文 and a newline\n"}
        expected = (json.dumps(value, indent=2, sort_keys=True)+"\n").encode("utf-8")
        encoding = wrapper.encoding
        with contextlib.redirect_stdout(wrapper): output(value, None)
        self.assertEqual(raw.getvalue(), expected)
        self.assertNotIn(b"\r\n", raw.getvalue())
        self.assertEqual(wrapper.encoding, encoding)
        wrapper.detach()

    def test_nonbinary_embedding_sink_has_typed_refusal_without_text_output(self):
        text = io.StringIO()
        with contextlib.redirect_stdout(text), self.assertRaisesRegex(Error, "binary buffer"):
            output({"x": "small valid output"}, None)
        self.assertEqual(text.getvalue(), "")


if __name__ == "__main__": unittest.main()
