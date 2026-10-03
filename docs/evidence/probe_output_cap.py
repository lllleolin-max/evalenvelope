"""A supported compact state must not be successfully exported unreadably.
Synthetic local receipt metadata is unauthenticated. All calls use the installed
registered console entry point obtained from that interpreter's sysconfig.
"""
import json
import os
from pathlib import Path
import subprocess
import sysconfig
import tempfile
from evalenvelope import parse_manifest, empty_state

CAP = 4 * 1024 * 1024
raw = {"version": 1, "kind": "independent_boxes",
       "identity": {"manifest": "file-cap-probe", "old_model": "old", "new_model": "new", "scorer": "s"},
       "strata": {"s": "1"}, "items": [{"id": "i", "stratum": "s",
       "old": {"low": "0", "high": "0", "cost": "1"},
       "new": {"low": "0", "high": "0", "cost": "1"}}]}
m = parse_manifest(raw)
state = empty_state(m).data()
state["receipts"] = [{"plan_digest": "a"*64, "prior_state_digest": "b"*64, "event_ids": []}
                     for _ in range(999)]
state["receipts"][0]["event_ids"] = ["x"]
compact = lambda v: json.dumps(v, separators=(",", ":")).encode("utf-8")
state["receipts"][0]["event_ids"] = ["x" * (CAP - 100 - len(compact(state)) + 1)]
source = compact(state)
assert len(source) == CAP - 100
observations = {"version": 1, "kind": "actual_observations", "identity": dict(m.identity),
                "manifest_digest": m.fingerprint, "observations": []}
cli = Path(sysconfig.get_path("scripts"))/("evalenvelope.exe" if os.name == "nt" else "evalenvelope")
result = {"synthetic": True, "receipt_declarations": 999, "state_input_bytes": len(source),
          "file_cap_bytes": CAP, "expected": "typed output-cap refusal preserving destination, or a readable exported state"}
with tempfile.TemporaryDirectory() as temp:
    d = Path(temp)
    (d/"manifest.json").write_bytes(compact(raw)); (d/"state.json").write_bytes(source)
    (d/"observations.json").write_bytes(compact(observations))
    out = d/"export.json"; out.write_bytes(b"preserved-existing-output")
    p = subprocess.run([str(cli), "import", "--manifest", str(d/"manifest.json"), "--state", str(d/"state.json"),
                        "--observations", str(d/"observations.json"), "--output", str(out)], capture_output=True, text=True)
    result["import_exit"] = p.returncode
    if p.returncode == 2:
        result.update(typed_refusal=True, error=json.loads(p.stderr)["error"],
                      destination_preserved=out.read_bytes()==b"preserved-existing-output",
                      source_preserved=(d/"state.json").read_bytes()==source)
        print(json.dumps(result, indent=2))
        assert result["destination_preserved"] and result["source_preserved"]
    else:
        result.update(typed_refusal=False, exported_bytes=out.stat().st_size)
        check = subprocess.run([str(cli), "analyze", "--manifest", str(d/"manifest.json"), "--state", str(out)], capture_output=True, text=True)
        result["exported_state_read_exit"] = check.returncode
        if check.returncode: result["read_error"] = json.loads(check.stderr)["error"]
        print(json.dumps(result, indent=2))
        assert p.returncode == 0 and check.returncode == 0, "successful export exceeded its own reader cap"
