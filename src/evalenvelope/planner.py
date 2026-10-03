"""Bounded exact prior-only action search. Values of future scores are not inputs."""
from dataclasses import dataclass
from fractions import Fraction
from .model import Error, number, count, fields, box_for, require_state


@dataclass(frozen=True)
class Action:
    id: str
    item: str
    stratum: str
    arms: tuple
    cost: Fraction
    reduction: Fraction

    def data(self):
        return {"id": self.id, "item": self.item, "stratum": self.stratum, "arms": list(self.arms),
                "cost": str(self.cost), "reduction": str(self.reduction)}


def actions(manifest, state):
    seen, result = state.seen(), []
    for i in manifest.items:
        missing = tuple(a for a in ("old", "new") if (i.id, a) not in seen)
        for arm in missing:
            lo, hi = box_for(i, arm, seen)
            result.append(Action(i.id + ":" + arm, i.id, i.stratum, (arm,), getattr(i, arm).cost,
                                 i.weight * (hi-lo)))
        if len(missing) == 2 and i.bundle_cost is not None:
            result.append(Action(i.id + ":both", i.id, i.stratum, ("old", "new"), i.bundle_cost,
                                 i.weight * (i.old.high-i.old.low+i.new.high-i.new.low)))
    return tuple(sorted(result, key=lambda a: a.id))


def requirements(manifest, options):
    fields(options, ("budget",), ("pins", "coverage", "max_nodes"))
    budget = number(options["budget"])
    if budget < 0:
        raise Error("negative budget")
    pins, coverage = options.get("pins", []), options.get("coverage", {})
    if not isinstance(pins, list) or any(not isinstance(p, str) for p in pins) or len(pins) != len(set(pins)):
        raise Error("pins must be unique action IDs")
    if not isinstance(coverage, dict) or set(coverage) - set(dict(manifest.strata)):
        raise Error("coverage must name declared strata")
    coverage = {s: count(v, 500) for s, v in sorted(coverage.items())}
    nodes = count(options.get("max_nodes", 100000), 1000000)
    if nodes == 0:
        raise Error("max_nodes must be positive")
    return {"budget": str(budget), "pins": sorted(pins), "coverage": coverage, "max_nodes": nodes}


def feasible(manifest, state, selected, req):
    acquired = {(a.item, arm) for a in selected for arm in a.arms}
    if sum(len(a.arms) for a in selected) != len(acquired):
        return False
    if sum(a.cost for a in selected) > number(req["budget"]):
        return False
    if not set(req["pins"]) <= {a.id for a in selected}:
        return False
    seen = set(state.seen()) | acquired
    for s, minimum in req["coverage"].items():
        if sum(i.stratum == s and (i.id, "old") in seen and (i.id, "new") in seen for i in manifest.items) < minimum:
            return False
    return True


def plan(manifest, state, options):
    require_state(manifest, state)
    req, all_actions = requirements(manifest, options), actions(manifest, state)
    if len(all_actions) > 32:
        raise Error("at most 32 candidate actions supported; partition collection rounds explicitly")
    if set(req["pins"]) - {a.id for a in all_actions}:
        raise Error("pinned action is unavailable or unknown")
    best, best_key, nodes, exhausted = None, None, 0, False
    budget = number(req["budget"])

    def visit(pos, selected, used, cost, reduction):
        nonlocal best, best_key, nodes, exhausted
        if nodes >= req["max_nodes"]:
            exhausted = True
            return
        nodes += 1
        if cost > budget:
            return
        if feasible(manifest, state, selected, req):
            key = (-reduction, cost, tuple(a.id for a in selected))
            if best_key is None or key < best_key:
                best, best_key = selected, key
        if pos == len(all_actions):
            return
        a = all_actions[pos]
        cells = {(a.item, arm) for arm in a.arms}
        if not used & cells:
            visit(pos+1, selected+(a,), used | cells, cost+a.cost, reduction+a.reduction)
        visit(pos+1, selected, used, cost, reduction)

    visit(0, (), set(), Fraction(0), Fraction(0))
    width = sum(i.weight * (box_for(i, "old", state.seen())[1]-box_for(i, "old", state.seen())[0]
                           +box_for(i, "new", state.seen())[1]-box_for(i, "new", state.seen())[0])
                for i in manifest.items)
    reduction = sum(a.reduction for a in best) if best is not None else None
    return {"version": 1, "kind": "prior_acquisition_plan", "identity": dict(manifest.identity),
            "manifest_digest": manifest.fingerprint, "prior_state_digest": state.fingerprint,
            "requirements": req, "status": "UNKNOWN" if exhausted else "OPTIMAL" if best is not None else "INFEASIBLE",
            "nodes": nodes, "selected": [a.data() for a in best] if best is not None else None,
            "cost": str(sum(a.cost for a in best)) if best is not None else None,
            "reduction": str(reduction) if reduction is not None else None,
            "remaining_width": str(width-reduction) if reduction is not None else None,
            "reduction_upper_bound": str(width) if exhausted else str(reduction) if reduction is not None else None,
            "objective": "maximize_prior_width_reduction_then_min_cost_then_lexical_action_ids"}
