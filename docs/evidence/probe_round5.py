"""Malformed certificate boundary returns typed refusals, unchanged probe."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sysconfig
import tempfile
from evalenvelope import parse_manifest, empty_state, envelope, plan, check_plan, check_envelope, Error
raw = {"version": 1, "kind": "independent_boxes", "identity": {"manifest": "malformed", "old_model": "old", "new_model": "new", "scorer": "judge"}, "strata": {"main": "1"},
       "items": [{"id": "case", "stratum": "main", "old": {"low": "0", "high": "1", "cost": "1"}, "new": {"low": "0", "high": "1", "cost": "1"}}]}
m = parse_manifest(raw); s = empty_state(m)
p = plan(m, s, {"budget": "1"}); bad_p = copy.deepcopy(p); bad_p["selected"][0]["id"] = ["case:new"]
c = envelope(m, s); bad_c = copy.deepcopy(c); bad_c["witnesses"]["lower"][0]["item"] = ["case"]
failures = []
for label, operation in (("unhashable selected action ID", lambda: check_plan(m, s, bad_p)), ("unhashable witness item", lambda: check_envelope(m, s, bad_c))):
    try: operation()
    except Error: print(label+": typed refusal")
    except Exception as exc: failures.append(label+": leaked "+type(exc).__name__)
    else: failures.append(label+": accepted")
cli = Path(sysconfig.get_path("scripts"))/("evalenvelope.exe" if os.name == "nt" else "evalenvelope")
with tempfile.TemporaryDirectory() as temp:
    directory = Path(temp); manifest = directory/"manifest.json"; cert = directory/"certificate.json"
    manifest.write_text(json.dumps(raw), encoding="utf-8"); cert.write_text("[]", encoding="utf-8")
    result = subprocess.run([str(cli), "check", "--manifest", str(manifest), "--certificate", str(cert)], capture_output=True, text=True)
    if result.returncode != 2 or "Traceback" in result.stderr: failures.append("non-object CLI certificate leaks traceback/exit="+str(result.returncode))
    else: print("non-object certificate: CLI exit 2")
assert not failures, "malformed-input refusal boundary failures: "+str(failures)
print("PASS: malformed inputs refuse without a Python exception traceback")
