"""Fair tiny same-constraint baseline; no incumbent software is executed."""
from fractions import Fraction
from itertools import combinations
import json
from evalenvelope import parse_manifest, empty_state, plan, check_plan
from evalenvelope.checker import independent_actions


def compare(weights, costs, budget, coverage=0):
    raw = {"version": 1, "kind": "independent_boxes", "identity": {"manifest": "contrast", "old_model": "old", "new_model": "new", "scorer": "s"},
           "strata": {f"g{x}": str(w) for x, w in enumerate(weights)}, "items": []}
    for x, cost in enumerate(costs):
        raw["items"].append({"id": f"i{x}", "stratum": f"g{x}", "old": {"low": "0", "high": "0", "cost": str(cost)}, "new": {"low": "0", "high": "1", "cost": str(cost)}})
    m = parse_manifest(raw); state = empty_state(m)
    options = {"budget": str(budget), "coverage": {f"g{x}": coverage for x in range(len(weights))}}
    optimized = plan(m, state, options)
    check_plan(m, state, optimized, True)
    candidates = independent_actions(m, state)
    # Zero-width records offer no uncertainty benefit, except when required
    # for completed-pair coverage. Prefer beneficial cheap actions first.
    order = sorted(candidates, key=lambda k: (candidates[k][3] == 0, candidates[k][2], k))
    # Enumerating feasibility gives both strategies exactly the same hard constraints.
    # The baseline greedily prefers inclusion of cheapest actions; no future values.
    feasible = []
    for size in range(len(order)+1):
        for subset in combinations(order, size):
            cost = sum(candidates[k][2] for k in subset)
            if cost > budget: continue
            cells = {(candidates[k][0].id, a) for k in subset for a in candidates[k][1]}
            if any(sum(i.stratum == s and (i.id,"old") in cells and (i.id,"new") in cells for i in m.items) < v for s,v in options["coverage"].items()): continue
            gain = sum(candidates[k][3] for k in subset)
            feasible.append((tuple(-int(k in subset) for k in order), tuple(sorted(subset)), cost, gain))
    cheapest = min(feasible) if feasible else None
    return {"budget": str(budget), "coverage": options["coverage"], "optimized_status": optimized["status"], "optimized_actions": [r["id"] for r in optimized["selected"]] if optimized["selected"] is not None else None,
            "optimized_reduction": optimized["reduction"], "baseline_actions": list(cheapest[1]) if cheapest else None, "baseline_reduction": str(cheapest[3]) if cheapest else None}


def main():
    cases = {"higher_weight_collects_more": compare([Fraction(1,10),Fraction(9,10)], [1,3], 3),
             "equal_cost_gain": compare([Fraction(1,2),Fraction(1,2)], [1,1], 2),
             "full_coverage_same": compare([Fraction(1,10),Fraction(9,10)], [1,3], 8, 1),
             "infeasible_same": compare([Fraction(1,2),Fraction(1,2)], [1,1], 1, 1)}
    assert cases["higher_weight_collects_more"]["optimized_reduction"] == "9/10"
    assert cases["higher_weight_collects_more"]["baseline_reduction"] == "1/10"
    assert cases["equal_cost_gain"]["optimized_reduction"] == cases["equal_cost_gain"]["baseline_reduction"]
    assert cases["infeasible_same"]["optimized_status"] == "INFEASIBLE"
    print(json.dumps({"data": "synthetic", "baseline": "cheapest-first preference over same hard-feasible subsets", "cases": cases}, indent=2))


if __name__ == "__main__": main()
