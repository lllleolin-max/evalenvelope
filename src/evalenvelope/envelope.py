"""Tight exact endpoints under independent per-score boxes."""
from .model import number, box_for, require_state, derived_text, source_text


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
        contributions.append({"item": i.id, "stratum": i.stratum, "weight": derived_text(i.weight),
                              "lower": derived_text(a), "upper": derived_text(b)})
        for side, old, new in (("lower", oh, nl), ("upper", ol, nh)):
            witnesses[side].append({"item": i.id, "old": derived_text(old), "new": derived_text(new)})
    return {"version": 1, "kind": "completion_certificate", "identity": dict(manifest.identity),
            "manifest_digest": manifest.fingerprint, "prior_state_digest": state.fingerprint,
            "margin": source_text(threshold), "lower": derived_text(low), "upper": derived_text(high), "width": derived_text(high-low),
            "decision": "PASS" if low >= threshold else "FAIL" if high < threshold else "INCONCLUSIVE",
            "estimand": "full_fixed_finite_manifest", "constraint_model": "independent_boxes",
            "contributions": contributions, "witnesses": {"kind": "constructed_not_observed", **witnesses}}
