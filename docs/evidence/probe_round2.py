"""Lossless JSON and exact schema-version boundary, unchanged before/after."""
import copy
import json
from pathlib import Path
import subprocess
import sysconfig
import tempfile
from evalenvelope import parse_manifest, empty_state, envelope, check_envelope, Error

raw = {"version": 1, "kind": "independent_boxes", "identity": {"manifest": "fixed", "old_model": "old-a", "new_model": "new-a", "scorer": "judge"}, "strata": {"main": "1"},
       "items": [{"id": "case", "stratum": "main", "old": {"low": "0", "high": "1", "cost": "1"}, "new": {"low": "0", "high": "1", "cost": "1"}}]}
failures = []
boolean = copy.deepcopy(raw); boolean["version"] = True
try: parse_manifest(boolean)
except Error: print("boolean manifest version: rejected")
else: failures.append("boolean manifest version")
m = parse_manifest(raw); s = empty_state(m); c = envelope(m, s); c["version"] = True
try: check_envelope(m, s, c)
except Error: print("boolean certificate version: rejected")
else: failures.append("boolean certificate version")
cli = Path(sysconfig.get_path("scripts"))/("evalenvelope.exe" if __import__("os").name == "nt" else "evalenvelope")
with tempfile.TemporaryDirectory() as temp:
    file = Path(temp)/"manifest.json"
    payload = json.dumps(raw).replace('"version": 1', '"version": 99, "version": 1')
    file.write_text(payload, encoding="utf-8")
    result = subprocess.run([str(cli), "analyze", "--manifest", str(file)], capture_output=True, text=True)
    if result.returncode == 2 and "duplicate" in result.stderr.lower(): print("duplicate JSON object key: rejected by registered CLI")
    else: failures.append("duplicate JSON object key accepted, exit="+str(result.returncode))
assert not failures, "strict input boundary failures: "+str(failures)
print("PASS: exact version and duplicate-key CLI boundary")
