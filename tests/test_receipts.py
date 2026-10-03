"""Supported state closure at the frozen-plan receipt resource boundary."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sysconfig
import tempfile
import unittest
from evalenvelope import (Error, parse_manifest, empty_state, parse_state,
                          plan, import_observations)
from evalenvelope.model import digest


def raw_manifest(dynamic=False):
    return {"version": 1, "kind": "independent_boxes", "identity": {"manifest": "receipt-tests", "old_model": "old", "new_model": "new", "scorer": "judge"},
            "strata": {"s": "1"}, "items": [{"id": "i", "stratum": "s", "old": {"low": "0", "high": "1" if dynamic else "0", "cost": "1"},
                                                "new": {"low": "0", "high": "1" if dynamic else "0", "cost": "1"}}]}


def state_with_receipts(m, n, observations=None):
    raw = empty_state(m).data()
    raw["receipts"] = [{"plan_digest": "a"*64, "prior_state_digest": "b"*64, "event_ids": []} for _ in range(n)]
    raw["observations"] = observations or []
    return parse_state(m, raw)


def incoming(m, observations=None):
    return {"version": 1, "kind": "actual_observations", "identity": dict(m.identity), "manifest_digest": m.fingerprint,
            "observations": observations or []}


class ReceiptTests(unittest.TestCase):
    def test_999_to_1000_then_typed_cap_and_stale_plan_refusal(self):
        m = parse_manifest(raw_manifest()); prior = state_with_receipts(m, 999)
        frozen = plan(m, prior, {"budget": "0"})
        self.assertEqual(frozen["selected"], [])
        next_state = import_observations(m, prior, incoming(m), frozen)
        self.assertEqual(len(prior.receipts), 999)
        self.assertEqual(len(next_state.receipts), 1000)
        self.assertEqual(parse_state(m, next_state.data()), next_state)
        self.assertEqual(next_state.receipts[-1]["plan_digest"], digest(frozen))
        self.assertEqual(next_state.receipts[-1]["prior_state_digest"], prior.fingerprint)
        self.assertEqual(next_state.receipts[-1]["event_ids"], [])
        with self.assertRaises(Error): import_observations(m, next_state, incoming(m), frozen)
        fresh = plan(m, next_state, {"budget": "0"})
        fingerprint, snapshot = next_state.fingerprint, copy.deepcopy(next_state.data())
        with self.assertRaisesRegex(Error, "receipt cap"): import_observations(m, next_state, incoming(m), fresh)
        self.assertEqual(next_state.fingerprint, fingerprint)
        self.assertEqual(next_state.data(), snapshot)
        self.assertEqual(import_observations(m, next_state, incoming(m)), next_state)

    def test_duplicate_declarations_and_actual_event_conflicts_at_cap(self):
        m = parse_manifest(raw_manifest(True))
        obs = {"event_id": "event", "item": "i", "arm": "old", "value": "0", "source": "synthetic", "kind": "actual"}
        full = state_with_receipts(m, 1000, [obs])
        self.assertEqual(len(full.receipts), 1000)  # local duplicate declarations are counted, not authenticated/deduplicated
        self.assertEqual(import_observations(m, full, incoming(m, [obs])), full)
        snapshot = copy.deepcopy(full.data())
        with self.assertRaises(Error): import_observations(m, full, incoming(m, [dict(obs, value="1")]))
        self.assertEqual(full.data(), snapshot)
        new_plan = plan(m, full, {"budget": "1", "pins": ["i:new"]})
        new_obs = dict(obs, event_id="event-new", arm="new")
        with self.assertRaisesRegex(Error, "receipt cap"): import_observations(m, full, incoming(m, [new_obs]), new_plan)
        self.assertEqual(full.data(), snapshot)

    def test_registered_cli_threshold_and_noop_output_preservation(self):
        m = parse_manifest(raw_manifest()); cli = Path(sysconfig.get_path("scripts"))/("evalenvelope.exe" if os.name == "nt" else "evalenvelope")
        self.assertTrue(cli.is_file(), "install an ordinary wheel before testing")
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            def save(name, value):
                p = d/name; p.write_text(json.dumps(value), encoding="utf-8"); return p
            manifest = save("manifest.json", raw_manifest()); state999 = save("state999.json", state_with_receipts(m, 999).data())
            empty = save("observations.json", incoming(m)); options = save("options.json", {"budget": "0"})
            def call(command, args):
                return subprocess.run([str(cli), command, "--manifest", str(manifest), *[str(a) for a in args]], capture_output=True, text=True)
            frozen999 = d/"plan999.json"
            r = call("plan", ["--state", state999, "--options", options, "--output", frozen999]); self.assertEqual(r.returncode, 0, r.stderr)
            state1000 = d/"state1000.json"
            r = call("import", ["--state", state999, "--observations", empty, "--frozen-plan", frozen999, "--output", state1000]); self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(len(parse_state(m, json.loads(state1000.read_text(encoding="utf-8"))).receipts), 1000)
            frozen1000 = d/"plan1000.json"
            r = call("plan", ["--state", state1000, "--options", options, "--output", frozen1000]); self.assertEqual(r.returncode, 0, r.stderr)
            destination = d/"preserved.json"; destination.write_bytes(b"preserved-existing-output")
            source_bytes = state1000.read_bytes()
            r = call("import", ["--state", state1000, "--observations", empty, "--frozen-plan", frozen1000, "--output", destination])
            self.assertEqual(r.returncode, 2); self.assertIn("receipt cap", r.stderr); self.assertNotIn("Traceback", r.stderr)
            self.assertEqual(destination.read_bytes(), b"preserved-existing-output")
            self.assertEqual(state1000.read_bytes(), source_bytes)
            r = call("import", ["--state", state1000, "--observations", empty, "--output", destination]); self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(destination.read_bytes(), source_bytes)


if __name__ == "__main__": unittest.main()
