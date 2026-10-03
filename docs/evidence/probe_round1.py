"""Public SDK foreign-state binding probe; same exact script before/after."""
import copy
from evalenvelope import parse_manifest, empty_state, envelope, plan, import_observations, Error

raw = {"version": 1, "kind": "independent_boxes", "identity": {"manifest": "fixed", "old_model": "old-a", "new_model": "new-a", "scorer": "judge"}, "strata": {"main": "1"},
       "items": [{"id": "case", "stratum": "main", "old": {"low": "0", "high": "1", "cost": "1"}, "new": {"low": "0", "high": "1", "cost": "1"}}]}
a = parse_manifest(raw)
changed = copy.deepcopy(raw); changed["identity"]["new_model"] = "new-b"
b = parse_manifest(changed)
foreign = empty_state(a)
import_doc = {"version": 1, "kind": "actual_observations", "identity": dict(b.identity), "manifest_digest": b.fingerprint, "observations": []}
failures = []
for name, operation in (("envelope", lambda: envelope(b, foreign)), ("plan", lambda: plan(b, foreign, {"budget": "1"})), ("import", lambda: import_observations(b, foreign, import_doc))):
    try: operation()
    except Error: print(name+": rejected foreign state")
    else: failures.append(name)
assert not failures, "foreign immutable model state accepted by SDK: "+str(failures)
print("PASS: all public analysis/import SDK boundaries reject foreign state")
