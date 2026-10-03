"""Full-state idempotency/resource-cap probe; unchanged before/after."""
from evalenvelope import parse_manifest, empty_state, import_observations, Error

raw = {"version": 1, "kind": "independent_boxes", "identity": {"manifest": "full", "old_model": "old", "new_model": "new", "scorer": "judge"}, "strata": {"main": "1"},
       "items": [{"id": "s"+str(i), "stratum": "main", "old": {"low": "0", "high": "1", "cost": "1"}, "new": {"low": "0", "high": "1", "cost": "1"}} for i in range(500)]}
m = parse_manifest(raw)
rows = [{"event_id": "e-"+i.id+"-"+arm, "item": i.id, "arm": arm, "value": "1/2", "source": "actual-fixture-run", "kind": "actual"} for i in m.items for arm in ("old", "new")]
doc = {"version": 1, "kind": "actual_observations", "identity": dict(m.identity), "manifest_digest": m.fingerprint, "observations": rows}
full = import_observations(m, empty_state(m), doc)
assert len(full.observations) == 1000
failures = []
for label, repeated in (("one-event replay", rows[:1]), ("full-export replay", rows)):
    try:
        result = import_observations(m, full, dict(doc, observations=repeated))
    except Error as exc: failures.append(label+": "+str(exc))
    else:
        assert result == full
        print(label+": idempotent, 1000 unique observations retained")
bad = dict(rows[0], value="0")
try: import_observations(m, full, dict(doc, observations=[bad]))
except Error: print("conflicting replay: rejected")
else: failures.append("conflicting replay accepted")
assert not failures, "full-state idempotence violated: "+str(failures)
print("PASS: caps apply to unique stored events without breaking replay")
