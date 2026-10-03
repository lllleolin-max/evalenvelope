"""Tight exact endpoints under independent per-score boxes."""
from .model import number, box_for, require_state


def envelope(manifest, state, margin="0"):
    require_state(manifest, state)
    threshold = number(margin)
    seen = state.seen()
    low = high = 0
    witnesses = {"lower": [], "upper": []}
    contributions = []
    for i in manifest.items:
        ol, oh = box_for(i, "old", seen)
        nl, nh = box_for(i, "new", seen)
        a, b = i.weight * (nl - oh), i.weight * (nh - ol)
        low, high = low + a, high + b
        contributions.append({"item": i.id, "stratum": i.stratum, "weight": str(i.weight),
                              "lower": str(a), "upper": str(b)})
        for side, old, new in (("lower", oh, nl), ("upper", ol, nh)):
            witnesses[side].append({"item": i.id, "old": str(old), "new": str(new)})
    return {"version": 1, "kind": "completion_certificate", "identity": dict(manifest.identity),
            "manifest_digest": manifest.fingerprint, "prior_state_digest": state.fingerprint,
            "margin": str(threshold), "lower": str(low), "upper": str(high), "width": str(high-low),
            "decision": "PASS" if low >= threshold else "FAIL" if high < threshold else "INCONCLUSIVE",
            "estimand": "full_fixed_finite_manifest", "constraint_model": "independent_boxes",
            "contributions": contributions, "witnesses": {"kind": "constructed_not_observed", **witnesses}}
