"""Synthetic local score-export -> frozen collection -> checked release decision."""
import json
from pathlib import Path
import subprocess
import sys
from fractions import Fraction


def run(cli, directory):
    directory.mkdir(parents=True, exist_ok=True)
    ident = {"manifest": "release-eval-42", "old_model": "model-old-7", "new_model": "model-new-8", "scorer": "rubric-3"}
    manifest = {"version": 1, "kind": "independent_boxes", "identity": ident,
                "strata": {"quick": "1/5", "critical": "4/5"}, "items": []}
    for name, stratum, cost in (("quick-a", "quick", "1"), ("quick-b", "quick", "1"), ("critical-a", "critical", "3"), ("critical-b", "critical", "3")):
        manifest["items"].append({"id": name, "stratum": stratum, "old": {"low": "0", "high": "1", "cost": cost}, "new": {"low": "0", "high": "1", "cost": cost}})

    def save(name, obj):
        p = directory/name; p.write_text(json.dumps(obj, indent=2)+"\n", encoding="utf-8"); return str(p)

    def call(command, name, **opts):
        output = directory/name
        args = [str(cli), command, "--manifest", str(directory/"manifest.json"), "--output", str(output)]
        for k, v in opts.items():
            args.extend(["--"+k.replace("_", "-"), str(v)])
        subprocess.run(args, check=True, capture_output=True, text=True)
        return json.loads(output.read_text(encoding="utf-8"))

    save("manifest.json", manifest)
    s0 = call("init", "empty.json")

    def export(rows):
        return {"version": 1, "kind": "actual_observations", "identity": ident, "manifest_digest": s0["manifest_digest"],
                "observations": [{"event_id": f"run1-{i}-{a}", "item": i, "arm": a, "value": v, "source": "synthetic-execution-1", "kind": "actual"} for i, a, v in rows]}

    prior = [("quick-a", "old", "0"), ("quick-a", "new", "1"), ("quick-b", "old", "0"), ("quick-b", "new", "1"), ("critical-a", "old", "1"), ("critical-b", "old", "1")]
    save("initial-observations.json", export(prior))
    call("import", "prior.json", state=directory/"empty.json", observations=directory/"initial-observations.json")
    before = call("analyze", "before.json", state=directory/"prior.json")
    call("check", "before-check.json", state=directory/"prior.json", certificate=directory/"before.json")
    save("options.json", {"budget": "6", "coverage": {"critical": 2}, "pins": [], "max_nodes": 10000})
    p = call("plan", "frozen-plan.json", state=directory/"prior.json", options=directory/"options.json")
    call("check", "plan-check.json", state=directory/"prior.json", certificate=directory/"frozen-plan.json")
    # The actual-value file is created only after the CLI has frozen the plan.
    # These are independently declared fixture values, not certificate witnesses.
    actual = export([("critical-a", "new", "0"), ("critical-b", "new", "0")])
    save("revealed-synthetic-observations.json", actual)
    call("import", "after-state.json", state=directory/"prior.json", observations=directory/"revealed-synthetic-observations.json", frozen_plan=directory/"frozen-plan.json")
    after = call("analyze", "after.json", state=directory/"after-state.json")
    call("check", "after-check.json", state=directory/"after-state.json", certificate=directory/"after.json")
    summary = {"data": "synthetic_fixture_scores_actually_imported", "completed_only_before": "1", "completed_only_wrong_decision": "PASS", "before": {k: before[k] for k in ("lower", "upper", "width", "decision")},
               "frozen_actions": [r["id"] for r in p["selected"]], "actual_after": {k: after[k] for k in ("lower", "upper", "width", "decision")}, "complete_weighted_baseline": "-3/5", "complete_data_agrees": after["lower"] == after["upper"] == "-3/5"}
    save("summary.json", summary)
    assert before["decision"] == "INCONCLUSIVE" and after["decision"] == "FAIL" and summary["complete_data_agrees"]
    return summary


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1], Path(sys.argv[2])), indent=2))
