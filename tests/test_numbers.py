"""Independent Fraction oracles for legal derived encodings and actual CLI."""
import copy
from fractions import Fraction
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile
import unittest
from evalenvelope import (Error, parse_manifest, empty_state, parse_state,
                          import_observations, envelope, plan, check_envelope, check_plan)
from evalenvelope.model import (number, derived_text, derived_number, source_text,
                                DERIVED_COMPONENT_DIGITS, DERIVED_MAX_CHARS)


def manifest_raw(n, base=10**70):
    return {"version": 1, "kind": "independent_boxes", "identity": {"manifest": "large-exact", "old_model": "old", "new_model": "new", "scorer": "judge"},
            "strata": {"main": "1"}, "items": [{"id": "s"+str(i), "stratum": "main",
                "old": {"low": "0", "high": "0", "cost": "1"},
                "new": {"low": "1/"+str(base+2*i+31), "high": "1/"+str(base+2*i+31), "cost": "1"}} for i in range(n)]}


class NumberTests(unittest.TestCase):
    def test_entire_generated_json_size_bound_fits_reader(self):
        # This deliberately non-semantic shape is only a byte-count upper
        # bound; it is neither an observation nor a completion certificate.
        m = parse_manifest(manifest_raw(1)); s = empty_state(m)
        c = envelope(m, s)
        c["identity"] = {key: "x"*100 for key in c["identity"]}
        c.update(margin="9"*128, lower="9"*387131, upper="9"*387131,
                 width="9"*643131, decision="INCONCLUSIVE")
        c["contributions"] = [{"item": "x"*100, "stratum": "x"*100,
                                "weight": "9"*263, "lower": "9"*905,
                                "upper": "9"*905} for _ in range(500)]
        for side in ("lower", "upper"):
            c["witnesses"][side] = [{"item": "x"*100, "old": "9"*258,
                                      "new": "9"*258} for _ in range(500)]
        size = len((json.dumps(c, indent=2, sort_keys=True)+"\n").encode("utf-8"))
        self.assertLess(size, 4*1024*1024)
        p = plan(m, s, {"budget": "2", "max_nodes": 1})
        p["identity"] = c["identity"]
        p.update(status="UNKNOWN", cost="9"*8324, reduction="9"*643131,
                 remaining_width="9"*643131, reduction_upper_bound="9"*643131,
                 nodes=1000000)
        p["selected"] = [{"id": "x"*100+":both", "item": "x"*100,
                           "stratum": "x"*100, "arms": ["old", "new"],
                           "cost": "9"*258, "reduction": "9"*1417} for _ in range(32)]
        p["requirements"] = {"budget": "9"*128, "pins": ["x"*100+":both"]*32,
                               "coverage": {str(k).zfill(3)+"x"*97: 500 for k in range(100)},
                               "max_nodes": 1000000}
        size = len((json.dumps(p, indent=2, sort_keys=True)+"\n").encode("utf-8"))
        self.assertLess(size, 4*1024*1024)

    def test_legal_source_sum_above_literal_cap(self):
        raw = manifest_raw(2); m = parse_manifest(raw); s = empty_state(m)
        expected = sum(Fraction(i["new"]["low"]) for i in raw["items"])/2
        cert = envelope(m, s)
        self.assertGreater(len(cert["lower"]), 128)
        self.assertEqual(Fraction(cert["lower"]), expected)
        self.assertTrue(check_envelope(m, s, cert)["valid"])
        bad = copy.deepcopy(cert); bad["lower"] = "0"
        with self.assertRaises(Error): check_envelope(m, s, bad)

    def test_integer_above_python_digit_limit_without_setting_change(self):
        before = sys.get_int_max_str_digits()
        integer = 10**5000+123
        encoded = "1"+"0"*4997+"123"
        self.assertEqual(derived_text(Fraction(integer)), encoded)
        self.assertEqual(derived_number(encoded), integer)
        self.assertEqual(derived_text(Fraction(-integer)), "-"+encoded)
        self.assertEqual(derived_number("-"+encoded), -integer)
        self.assertEqual(sys.get_int_max_str_digits(), before)
        if 0 < before < 5001:
            with self.assertRaises(ValueError): str(integer)
        with self.assertRaises(Error): number(integer)

    def test_derived_canonical_and_resource_refusals(self):
        for invalid in ("-0", "0/2", "1/1", "2/4", "01", "1.0", "+1", "-01", "1/00", "1/0", "1/02", 0, True):
            with self.assertRaises(Error): derived_number(invalid)
        for invalid in ("1"+"0"*DERIVED_COMPONENT_DIGITS, "1"*(DERIVED_MAX_CHARS+1)):
            with self.assertRaises(Error): derived_number(invalid)
        for invalid in ("1"*129, "1/"+"9"*127):
            with self.assertRaises(Error): number(invalid)
        m = parse_manifest(manifest_raw(2)); s = empty_state(m)
        cert = envelope(m, s)
        for change in (lambda d: d.update(width="-1"), lambda d: d.update(upper="2/4"),
                       lambda d: d["contributions"][0].update(weight="0/2"),
                       lambda d: d["witnesses"]["lower"][0].update(new="0/1")):
            bad = copy.deepcopy(cert); change(bad)
            with self.assertRaises(Error): check_envelope(m, s, bad)
        p = plan(m, s, {"budget": "4", "pins": ["s0:new"]})
        for field in ("cost", "reduction", "remaining_width", "reduction_upper_bound"):
            bad = copy.deepcopy(p); bad[field] = "-1"
            with self.assertRaises(Error): check_plan(m, s, bad)
        bad = copy.deepcopy(p); bad["selected"][0]["reduction"] = "00"
        with self.assertRaises(Error): check_plan(m, s, bad)

    def test_source_decimal_manifest_state_and_policy_roundtrip(self):
        decimal = "0."+"1234567890"*12+"123457"
        self.assertEqual(len(decimal), 128)
        self.assertGreater(len(str(Fraction(decimal))), 128)
        self.assertEqual(len(source_text(number(decimal))), 128)
        raw = manifest_raw(1)
        for arm in ("old", "new"):
            raw["items"][0][arm].update(low="0", high="1", cost=decimal)
        m = parse_manifest(raw)
        self.assertEqual(parse_manifest(m.data()), m)
        doc = {"version": 1, "kind": "actual_observations", "identity": dict(m.identity), "manifest_digest": m.fingerprint,
               "observations": [{"event_id": "run1", "item": "s0", "arm": "old", "value": decimal, "source": "synthetic", "kind": "actual"}]}
        s = import_observations(m, empty_state(m), doc)
        self.assertEqual(parse_state(m, s.data()), s)
        cert = envelope(m, s, decimal)
        check_envelope(m, s, cert)
        p = plan(m, s, {"budget": decimal})
        self.assertEqual(p["status"], "OPTIMAL")
        self.assertGreater(len(p["cost"]), 128)
        check_plan(m, s, p, True)
        from evalenvelope.cli import read
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp)/"huge-int.json"
            file.write_text('{"value":'+"1"*5000+'}', encoding="utf-8")
            with self.assertRaises(Error): read(file)

    def test_maximum_manifest_independent_endpoint_oracle(self):
        raw = manifest_raw(500, 10**40)
        m = parse_manifest(raw); s = empty_state(m)
        expected = sum(Fraction(row["new"]["low"]) for row in raw["items"])/500
        cert = envelope(m, s)
        self.assertEqual(derived_number(cert["lower"]), expected)
        self.assertTrue(check_envelope(m, s, cert)["valid"])

    def test_large_width_plan_fields_and_actual_cli(self):
        before = sys.get_int_max_str_digits()
        base = 10**120
        raw = manifest_raw(16, base)
        for k, row in enumerate(raw["items"]):
            offset = 8*k+1
            row["old"].update(low="1/"+str(base+offset+2), high="1/"+str(base+offset), cost="1/"+str(base+129+4*k))
            row["new"].update(low="1/"+str(base+offset+6), high="1/"+str(base+offset+4), cost="1/"+str(base+131+4*k))
        expected = sum((Fraction(row[arm]["high"])-Fraction(row[arm]["low"])) for row in raw["items"] for arm in ("old", "new"))/16
        m = parse_manifest(raw); s = empty_state(m)
        cert = envelope(m, s)
        self.assertGreater(max(len(part) for part in cert["width"].split("/")), 4300)
        self.assertEqual(derived_number(cert["width"]), expected)
        check_envelope(m, s, cert)
        pins = [row["id"]+":"+arm for row in raw["items"] for arm in ("old", "new")]
        options = {"budget": "1", "pins": pins, "max_nodes": 40}
        p = plan(m, s, options)
        self.assertEqual(p["status"], "UNKNOWN")
        self.assertEqual(len(p["selected"]), 32)
        self.assertEqual(derived_number(p["reduction"]), expected)
        self.assertEqual(derived_number(p["reduction_upper_bound"]), expected)
        expected_cost = sum(Fraction(row[arm]["cost"]) for row in raw["items"] for arm in ("old", "new"))
        self.assertEqual(derived_number(p["cost"]), expected_cost)
        check_plan(m, s, p)
        cli = Path(sysconfig.get_path("scripts"))/("evalenvelope.exe" if os.name == "nt" else "evalenvelope")
        self.assertTrue(cli.is_file(), "run tests against an installed ordinary wheel")
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp); manifest = d/"manifest.json"; opts = d/"options.json"
            manifest.write_text(json.dumps(raw), encoding="utf-8"); opts.write_text(json.dumps(options), encoding="utf-8")
            for command, extra, name in (("analyze", [], "envelope.json"), ("plan", ["--options", str(opts)], "plan.json")):
                out = d/name
                result = subprocess.run([str(cli), command, "--manifest", str(manifest), *extra, "--output", str(out)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                checked = subprocess.run([str(cli), "check", "--manifest", str(manifest), "--certificate", str(out)], capture_output=True, text=True)
                self.assertEqual(checked.returncode, 0, checked.stderr)
                self.assertTrue(json.loads(checked.stdout)["valid"])
        self.assertEqual(sys.get_int_max_str_digits(), before)


if __name__ == "__main__": unittest.main()
