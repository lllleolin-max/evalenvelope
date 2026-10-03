"""Strict immutable domain objects and actual-observation imports."""
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import re


class Error(ValueError):
    """Invalid or unsupported input; no result is certified."""


def fields(value, required, optional=()):
    if not isinstance(value, dict):
        raise Error("expected JSON object")
    if set(value) - set(required) - set(optional) or set(required) - set(value):
        raise Error(f"fields must include {sorted(required)}; optional {sorted(optional)}")


def number(value):
    # JSON floats would lose the declared exact decimal; use rational strings.
    if type(value) is int:
        value = str(value)
    if not isinstance(value, str) or len(value) > 128 or not re.fullmatch(r"-?\d+(?:/\d+|\.\d+)?", value):
        raise Error("exact number required: integer or decimal/rational string (128 chars max)")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise Error("invalid rational number") from exc


def count(value, maximum=1000000):
    if type(value) is not int or value < 0 or value > maximum:
        raise Error(f"integer count must lie in [0,{maximum}]")
    return value


def version_one(value):
    if type(value) is not int or value != 1:
        raise Error("schema version must be the integer 1")


def token(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", value):
        raise Error("IDs must be 1..100 ASCII letters/digits/_.-")
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def identity(value):
    fields(value, ("manifest", "old_model", "new_model", "scorer"))
    return tuple((key, token(value[key])) for key in sorted(value))


@dataclass(frozen=True)
class Box:
    low: Fraction
    high: Fraction
    cost: Fraction


@dataclass(frozen=True)
class Item:
    id: str
    stratum: str
    weight: Fraction
    old: Box
    new: Box
    bundle_cost: Fraction | None


@dataclass(frozen=True)
class Manifest:
    identity: tuple
    strata: tuple
    items: tuple
    fingerprint: str

    def data(self):
        return {"version": 1, "kind": "independent_boxes", "identity": dict(self.identity),
                "strata": {s: str(w) for s, w in self.strata},
                "items": [dict({"id": i.id, "stratum": i.stratum,
                    "old": {"low": str(i.old.low), "high": str(i.old.high), "cost": str(i.old.cost)},
                    "new": {"low": str(i.new.low), "high": str(i.new.high), "cost": str(i.new.cost)}},
                    **({"bundle_cost": str(i.bundle_cost)} if i.bundle_cost is not None else {})) for i in self.items]}


def parse_manifest(raw):
    fields(raw, ("version", "kind", "identity", "strata", "items"))
    version_one(raw["version"])
    if raw["kind"] != "independent_boxes":
        raise Error("only version 1 independent_boxes supported; coupled constraints are unsupported")
    ident = identity(raw["identity"])
    strata = raw["strata"]
    if not isinstance(strata, dict) or not strata or len(strata) > 100:
        raise Error("1..100 strata required")
    strata = tuple(sorted((token(s), number(w)) for s, w in strata.items()))
    if any(w < 0 for _, w in strata) or sum(w for _, w in strata) != 1:
        raise Error("fixed nonnegative stratum weights must sum exactly to one")
    rows = raw["items"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 500:
        raise Error("manifest requires 1..500 paired items")
    ids, parsed = set(), []
    for row in rows:
        fields(row, ("id", "stratum", "old", "new"), ("bundle_cost",))
        key, s = token(row["id"]), token(row["stratum"])
        if key in ids or s not in dict(strata):
            raise Error("duplicate item ID or undeclared stratum")
        ids.add(key)
        boxes = []
        for arm in ("old", "new"):
            fields(row[arm], ("low", "high", "cost"))
            lo, hi, cost = (number(row[arm][k]) for k in ("low", "high", "cost"))
            if lo > hi or cost < 0:
                raise Error("reversed score range or negative acquisition cost")
            boxes.append(Box(lo, hi, cost))
        bundle = number(row["bundle_cost"]) if "bundle_cost" in row else None
        if bundle is not None and bundle < 0:
            raise Error("negative bundle cost")
        parsed.append((key, s, *boxes, bundle))
    sizes = {s: sum(r[1] == s for r in parsed) for s, _ in strata}
    if any(n == 0 for n in sizes.values()):
        raise Error("every predeclared stratum needs a member, even at zero weight")
    items = tuple(Item(k, s, dict(strata)[s] / sizes[s], o, n, b)
                  for k, s, o, n, b in sorted(parsed))
    draft = Manifest(ident, strata, items, "")
    return Manifest(ident, strata, items, digest(draft.data()))


@dataclass(frozen=True)
class Observation:
    event_id: str
    item: str
    arm: str
    value: Fraction
    source: str

    def data(self):
        return {"event_id": self.event_id, "item": self.item, "arm": self.arm,
                "value": str(self.value), "source": self.source, "kind": "actual"}


@dataclass(frozen=True)
class State:
    manifest_digest: str
    identity: tuple
    observations: tuple
    receipts: tuple = ()

    def data(self):
        return {"version": 1, "kind": "observation_state", "identity": dict(self.identity),
                "manifest_digest": self.manifest_digest,
                "observations": [o.data() for o in self.observations],
                "receipts": list(self.receipts)}

    @property
    def fingerprint(self):
        return digest(self.data())

    def seen(self):
        return {(o.item, o.arm): o.value for o in self.observations}


def empty_state(manifest):
    return State(manifest.fingerprint, manifest.identity, ())


def require_state(manifest, state):
    """SDK calls must bind validated states just as the CLI parser does."""
    if not isinstance(state, State) or state.manifest_digest != manifest.fingerprint or state.identity != manifest.identity:
        raise Error("foreign manifest/model/scorer observation state")
    if observations(manifest, [o.data() for o in state.observations]) != state.observations:
        raise Error("observation state is not canonical")


def binding(manifest, raw):
    if identity(raw["identity"]) != manifest.identity or raw["manifest_digest"] != manifest.fingerprint:
        raise Error("foreign manifest/model/scorer identity")


def observations(manifest, rows, max_input_rows=1000):
    if not isinstance(rows, list) or len(rows) > max_input_rows:
        raise Error(f"observations must be a list of at most {max_input_rows} input records")
    by_id, by_cell = {}, {}
    items = {i.id: i for i in manifest.items}
    for row in rows:
        fields(row, ("event_id", "item", "arm", "value", "source", "kind"))
        event, key, source = token(row["event_id"]), token(row["item"]), token(row["source"])
        arm, value = row["arm"], number(row["value"])
        if row["kind"] != "actual" or key not in items or arm not in ("old", "new"):
            raise Error("actual observation for a known item/arm required; witnesses cannot be imported")
        box = getattr(items[key], arm)
        if not box.low <= value <= box.high:
            raise Error("observation outside declared score box")
        obs = Observation(event, key, arm, value, source)
        if event in by_id and by_id[event] != obs:
            raise Error("conflicting duplicate event ID")
        if (key, arm) in by_cell and by_cell[key, arm].value != value:
            raise Error("conflicting actual scores for one immutable sample/model/scorer")
        by_id[event] = obs
        by_cell[key, arm] = obs
    if len(by_id) > 1000:
        raise Error("observation state exceeds 1000 unique event records")
    return tuple(sorted(by_id.values(), key=lambda o: o.event_id))


def parse_state(manifest, raw):
    fields(raw, ("version", "kind", "identity", "manifest_digest", "observations", "receipts"))
    version_one(raw["version"])
    if raw["kind"] != "observation_state":
        raise Error("unsupported state")
    binding(manifest, raw)
    if not isinstance(raw["receipts"], list) or len(raw["receipts"]) > 1000:
        raise Error("invalid receipts")
    for r in raw["receipts"]:
        fields(r, ("plan_digest", "prior_state_digest", "event_ids"))
        if not all(isinstance(r[k], str) and len(r[k]) == 64 for k in ("plan_digest", "prior_state_digest")):
            raise Error("invalid receipt digest")
        if not isinstance(r["event_ids"], list) or any(not isinstance(e, str) for e in r["event_ids"]):
            raise Error("invalid receipt event IDs")
    return State(manifest.fingerprint, manifest.identity, observations(manifest, raw["observations"]),
                 tuple(raw["receipts"]))


def import_observations(manifest, state, raw, frozen_plan=None):
    require_state(manifest, state)
    fields(raw, ("version", "kind", "identity", "manifest_digest", "observations"))
    version_one(raw["version"])
    if raw["kind"] != "actual_observations":
        raise Error("actual_observations import required")
    binding(manifest, raw)
    incoming = observations(manifest, raw["observations"])
    # Each input and existing state is bounded separately. Replay overlap must
    # be removed before applying the stored unique-event cap.
    merged = observations(manifest, [o.data() for o in state.observations + incoming], max_input_rows=2000)
    receipts = state.receipts
    if frozen_plan is not None:
        from .checker import check_plan
        check_plan(manifest, state, frozen_plan)
        if frozen_plan["status"] == "INFEASIBLE" or frozen_plan["selected"] is None:
            raise Error("a feasible frozen acquisition plan is required")
        planned = {(r["item"], a) for r in frozen_plan["selected"] for a in r["arms"]}
        actual = {(o.item, o.arm) for o in incoming}
        if actual != planned:
            raise Error("import must fulfill exactly the frozen plan's acquisitions")
        receipts += ({"plan_digest": digest(frozen_plan), "prior_state_digest": state.fingerprint,
                      "event_ids": [o.event_id for o in incoming]},)
    return State(manifest.fingerprint, manifest.identity, merged, receipts)


def box_for(item, arm, seen):
    if (item.id, arm) in seen:
        v = seen[item.id, arm]
        return v, v
    b = getattr(item, arm)
    return b.low, b.high
