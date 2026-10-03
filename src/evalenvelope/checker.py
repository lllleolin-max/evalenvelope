"""Independent certificate checker; no calls to envelope/planner algorithms."""
from fractions import Fraction
from itertools import combinations
from .model import Error, fields, number, binding, count, require_state, version_one


def bound_to_state(manifest, state, document):
    require_state(manifest, state)
    binding(manifest, document)
    if document["prior_state_digest"] != state.fingerprint:
        raise Error("certificate is not bound to this observation state")


def check_envelope(manifest, state, certificate):
    fields(certificate, ("version", "kind", "identity", "manifest_digest", "prior_state_digest", "margin",
                        "lower", "upper", "width", "decision", "estimand", "constraint_model", "contributions", "witnesses"))
    bound_to_state(manifest, state, certificate)
    version_one(certificate["version"])
    if certificate["kind"] != "completion_certificate" or certificate["estimand"] != "full_fixed_finite_manifest" or certificate["constraint_model"] != "independent_boxes":
        raise Error("unsupported certificate")
    seen, expected_low, expected_high, contributions = state.seen(), Fraction(0), Fraction(0), []
    for i in manifest.items:
        old = (seen[i.id, "old"],)*2 if (i.id, "old") in seen else (i.old.low, i.old.high)
        new = (seen[i.id, "new"],)*2 if (i.id, "new") in seen else (i.new.low, i.new.high)
        a, b = i.weight*(new[0]-old[1]), i.weight*(new[1]-old[0])
        expected_low += a
        expected_high += b
        contributions.append({"item": i.id, "stratum": i.stratum, "weight": str(i.weight), "lower": str(a), "upper": str(b)})
    if certificate["contributions"] != contributions:
        raise Error("incorrect per-item contributions")
    if number(certificate["lower"]) != expected_low or number(certificate["upper"]) != expected_high or number(certificate["width"]) != expected_high-expected_low:
        raise Error("incorrect completion bounds")
    margin = number(certificate["margin"])
    decision = "PASS" if expected_low >= margin else "FAIL" if expected_high < margin else "INCONCLUSIVE"
    if certificate["decision"] != decision:
        raise Error("incorrect release decision")
    w = certificate["witnesses"]
    fields(w, ("kind", "lower", "upper"))
    if w["kind"] != "constructed_not_observed":
        raise Error("completion witness must be labeled constructed")
    for side, endpoint in (("lower", expected_low), ("upper", expected_high)):
        rows = w[side]
        if not isinstance(rows, list) or len(rows) != len(manifest.items):
            raise Error("witness must complete every manifest item exactly once")
        values = {}
        for row in rows:
            fields(row, ("item", "old", "new"))
            if row["item"] in values:
                raise Error("duplicate witness item")
            values[row["item"]] = (number(row["old"]), number(row["new"]))
        if set(values) != {i.id for i in manifest.items}:
            raise Error("foreign/missing witness item")
        total = Fraction(0)
        for i in manifest.items:
            old, new = values[i.id]
            for arm, value in (("old", old), ("new", new)):
                box = getattr(i, arm)
                if not box.low <= value <= box.high or ((i.id, arm) in seen and value != seen[i.id, arm]):
                    raise Error("illegal witness score or altered actual observation")
            total += i.weight*(new-old)
        if total != endpoint:
            raise Error("witness does not attain claimed endpoint")
    return {"valid": True, "scope": "tight_endpoints_and_actual_observation_preservation"}


def independent_actions(manifest, state):
    result, seen = {}, state.seen()
    for i in manifest.items:
        missing = [a for a in ("old", "new") if (i.id, a) not in seen]
        for arm in missing:
            b = getattr(i, arm)
            result[i.id+":"+arm] = (i, (arm,), b.cost, i.weight*(b.high-b.low))
        if len(missing) == 2 and i.bundle_cost is not None:
            result[i.id+":both"] = (i, ("old", "new"), i.bundle_cost,
                                    i.weight*(i.old.high-i.old.low+i.new.high-i.new.low))
    return result


def check_plan(manifest, state, document, prove_optimal=False):
    fields(document, ("version", "kind", "identity", "manifest_digest", "prior_state_digest", "requirements", "status", "nodes", "selected", "cost", "reduction", "remaining_width", "reduction_upper_bound", "objective"))
    bound_to_state(manifest, state, document)
    version_one(document["version"])
    if document["kind"] != "prior_acquisition_plan" or document["status"] not in ("UNKNOWN", "OPTIMAL", "INFEASIBLE"):
        raise Error("unsupported plan")
    req = document["requirements"]
    fields(req, ("budget", "pins", "coverage", "max_nodes"))
    budget = number(req["budget"])
    if budget < 0 or not isinstance(req["pins"], list) or any(not isinstance(p, str) for p in req["pins"]) or len(req["pins"]) != len(set(req["pins"])):
        raise Error("invalid requirements")
    if not isinstance(req["coverage"], dict) or set(req["coverage"]) - set(dict(manifest.strata)):
        raise Error("invalid coverage")
    for v in req["coverage"].values():
        count(v, 500)
    limit = count(req["max_nodes"])
    visited = count(document["nodes"])
    if limit == 0 or not 1 <= visited <= limit:
        raise Error("search evidence violates positive declared node budget")
    if document["objective"] != "maximize_prior_width_reduction_then_min_cost_then_lexical_action_ids":
        raise Error("unsupported acquisition objective")
    choices = independent_actions(manifest, state)
    if set(req["pins"]) - set(choices):
        raise Error("unavailable pin")
    width = sum(a[3] for key, a in choices.items() if not key.endswith(":both"))

    def valid(ids):
        cells, cost, gain = set(state.seen()), Fraction(0), Fraction(0)
        for key in ids:
            item, arms, price, reduction = choices[key]
            new_cells = {(item.id, a) for a in arms}
            if cells & new_cells:
                return None
            cells |= new_cells
            cost += price
            gain += reduction
        if cost > budget or not set(req["pins"]) <= set(ids):
            return None
        for s, minimum in req["coverage"].items():
            if sum(i.stratum == s and (i.id, "old") in cells and (i.id, "new") in cells for i in manifest.items) < minimum:
                return None
        return (-gain, cost, tuple(sorted(ids)))

    selected = document["selected"]
    ids = None
    if selected is not None:
        if not isinstance(selected, list):
            raise Error("invalid selected actions")
        ids = []
        for row in selected:
            fields(row, ("id", "item", "stratum", "arms", "cost", "reduction"))
            key = row["id"]
            if key not in choices or key in ids:
                raise Error("unknown or duplicate action")
            i, arms, cost, reduction = choices[key]
            if row != {"id": key, "item": i.id, "stratum": i.stratum, "arms": list(arms), "cost": str(cost), "reduction": str(reduction)}:
                raise Error("action altered from declared prior")
            ids.append(key)
        key = valid(ids)
        if key is None:
            raise Error("plan violates budget, coverage, pins or overlap")
        if number(document["cost"]) != key[1] or number(document["reduction"]) != -key[0] or number(document["remaining_width"]) != width+key[0]:
            raise Error("incorrect plan objective accounting")
    elif document["status"] == "OPTIMAL":
        raise Error("OPTIMAL requires a feasible plan")
    elif any(document[k] is not None for k in ("cost", "reduction", "remaining_width")):
        raise Error("missing incumbent must not advertise objective values")
    if document["status"] == "INFEASIBLE" and selected is not None:
        raise Error("infeasible claim contains an incumbent")
    if document["status"] == "UNKNOWN":
        if number(document["reduction_upper_bound"]) != width:
            raise Error("UNKNOWN requires the conservative full remaining-width upper bound")
    elif document["status"] == "INFEASIBLE":
        if document["reduction_upper_bound"] is not None:
            raise Error("INFEASIBLE must not advertise a reduction bound")
    elif number(document["reduction_upper_bound"]) != number(document["reduction"]):
        raise Error("OPTIMAL objective and reduction bound must agree")
    optimal = "not_checked"
    if prove_optimal:
        if len(choices) > 20:
            raise Error("independent exhaustive oracle limited to 20 actions")
        best = None
        keys = sorted(choices)
        for size in range(len(keys)+1):
            for subset in combinations(keys, size):
                candidate = valid(subset)
                if candidate is not None and (best is None or candidate < best):
                    best = candidate
        if document["status"] == "OPTIMAL" and (ids is None or valid(ids) != best):
            raise Error("optimality claim fails independent subset oracle")
        if document["status"] == "INFEASIBLE" and best is not None:
            raise Error("infeasibility claim fails independent subset oracle")
        optimal = "verified" if document["status"] != "UNKNOWN" else "UNKNOWN_retained"
    return {"valid": True, "scope": "feasibility_and_prior_objective", "optimality": optimal}
