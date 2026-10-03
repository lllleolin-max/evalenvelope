"""Independent UNKNOWN-plan bound/metadata checker probe, unchanged."""
import copy
from evalenvelope import parse_manifest, empty_state, plan, check_plan, Error
raw = {"version": 1, "kind": "independent_boxes", "identity": {"manifest": "bounded", "old_model": "old", "new_model": "new", "scorer": "judge"}, "strata": {"main": "1"},
       "items": [{"id": "case", "stratum": "main", "old": {"low": "0", "high": "1", "cost": "1"}, "new": {"low": "0", "high": "1", "cost": "1"}}]}
m = parse_manifest(raw); s = empty_state(m)
p = plan(m, s, {"budget": "1", "max_nodes": 1})
assert p["status"] == "UNKNOWN"
check_plan(m, s, p, True)
failures = []
for label, change in (("negative reduction upper bound", lambda d: d.update(reduction_upper_bound="-1")),
                       ("invented objective", lambda d: d.update(objective="uses_hidden_scores")),
                       ("exceeded declared node budget", lambda d: d.update(nodes=2)),
                       ("zero search budget", lambda d: d["requirements"].update(max_nodes=0))):
    bad = copy.deepcopy(p); change(bad)
    try: check_plan(m, s, bad, True)
    except Error: print(label+": rejected")
    else: failures.append(label)
assert not failures, "checker accepts unsupported bounded-search evidence: "+str(failures)
print("PASS: UNKNOWN remains honest and independently validated")
