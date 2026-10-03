import copy
from fractions import Fraction
from itertools import product, combinations
import random
import json
from pathlib import Path
import tempfile
import unittest
from evalenvelope import *
from evalenvelope.model import number


def fixture(n=2):
    return {"version": 1, "kind": "independent_boxes", "identity": {"manifest": "m", "old_model": "old-v1", "new_model": "new-v2", "scorer": "judge-v1"},
            "strata": {"main": "1"}, "items": [{"id": f"s{x}", "stratum": "main", "old": {"low": "0", "high": "1", "cost": "2"}, "new": {"low": "0", "high": "1", "cost": "1"}} for x in range(n)]}


def batch(m, rows):
    return {"version": 1, "kind": "actual_observations", "identity": dict(m.identity), "manifest_digest": m.fingerprint,
            "observations": [{"event_id": f"e-{i}-{a}", "item": i, "arm": a, "value": str(v), "source": "synthetic-run-1", "kind": "actual"} for i, a, v in rows]}


class CoreTests(unittest.TestCase):
    def test_foreign_sdk_state_rejected(self):
        raw = fixture(); a = parse_manifest(raw)
        raw["identity"]["new_model"] = "different-model"
        b = parse_manifest(raw); foreign = empty_state(a)
        for operation in (lambda: envelope(b, foreign), lambda: plan(b, foreign, {"budget": "1"}),
                          lambda: import_observations(b, foreign, batch(b, [])),
                          lambda: check_envelope(b, foreign, envelope(b, empty_state(b)))):
            with self.assertRaises(Error): operation()

    def test_exact_formula_and_witnesses(self):
        m = parse_manifest(fixture())
        s = import_observations(m, empty_state(m), batch(m, [("s0", "old", "1/2")]))
        c = envelope(m, s)
        self.assertEqual((c["lower"], c["upper"]), ("-3/4", "3/4"))
        self.assertTrue(check_envelope(m, s, c)["valid"])
        bad = copy.deepcopy(c)
        bad["witnesses"]["lower"][0]["old"] = "0"
        with self.assertRaises(Error): check_envelope(m, s, bad)

    def test_fixed_strata_and_zero_weight(self):
        raw = fixture(3)
        raw["strata"] = {"main": "1", "zero": "0"}
        raw["items"][2]["stratum"] = "zero"
        m = parse_manifest(raw)
        s = empty_state(m)
        p = plan(m, s, {"budget": "1", "pins": ["s2:new"]})
        self.assertEqual(p["reduction"], "0")
        self.assertEqual(p["remaining_width"], "2")
        self.assertTrue(check_plan(m, s, p, True)["valid"])

    def test_import_actual_conflicts_foreign_and_idempotence(self):
        m = parse_manifest(fixture())
        b = batch(m, [("s0", "new", "1")])
        s = import_observations(m, empty_state(m), b)
        self.assertEqual(import_observations(m, s, b), s)
        for field, value in (("manifest_digest", "x"), ("kind", "constructed_not_observed")):
            bad = copy.deepcopy(b); bad[field] = value
            with self.assertRaises(Error): import_observations(m, s, bad)
        bad = copy.deepcopy(b); bad["observations"][0]["value"] = "0"
        with self.assertRaises(Error): import_observations(m, s, bad)
        bad["observations"][0]["value"] = "2"
        with self.assertRaises(Error): import_observations(m, s, bad)

    def test_full_capacity_import_is_idempotent(self):
        m = parse_manifest(fixture(500))
        b = batch(m, [(i.id, a, "1/2") for i in m.items for a in ("old", "new")])
        full = import_observations(m, empty_state(m), b)
        self.assertEqual(len(full.observations), 1000)
        self.assertEqual(import_observations(m, full, b), full)
        self.assertEqual(import_observations(m, full, dict(b, observations=b["observations"][:1])), full)
        new_event = dict(b["observations"][0], event_id="extra-confirmation")
        with self.assertRaises(Error): import_observations(m, full, dict(b, observations=[new_event]))

    def test_plan_freeze_exact_actual_import(self):
        m = parse_manifest(fixture())
        s = empty_state(m)
        p = plan(m, s, {"budget": "2", "coverage": {}, "pins": []})
        self.assertEqual([a["id"] for a in p["selected"]], ["s0:new", "s1:new"])
        next_state = import_observations(m, s, batch(m, [("s0", "new", "1/3"), ("s1", "new", "2/3")]), p)
        self.assertEqual(envelope(m, next_state)["width"], "1")
        self.assertEqual(len(next_state.receipts), 1)
        with self.assertRaises(Error): import_observations(m, s, batch(m, [("s0", "old", "0")]), p)
        with self.assertRaises(Error): check_plan(m, next_state, p)

    def test_bundles_overlap_cost_and_coverage(self):
        raw = fixture(1); raw["items"][0]["bundle_cost"] = "2"
        m = parse_manifest(raw); s = empty_state(m)
        p = plan(m, s, {"budget": "2", "coverage": {"main": 1}})
        self.assertEqual([a["id"] for a in p["selected"]], ["s0:both"])
        check_plan(m, s, p, True)
        p = plan(m, s, {"budget": "1", "coverage": {"main": 1}})
        self.assertEqual(p["status"], "INFEASIBLE")
        check_plan(m, s, p, True)
        raw["items"][0].pop("bundle_cost")
        m = parse_manifest(raw); s = empty_state(m)
        p = plan(m, s, {"budget": "2", "pins": ["s0:old", "s0:new"]})
        self.assertEqual(p["status"], "INFEASIBLE")

    def test_margin_equality_and_unknown(self):
        m = parse_manifest(fixture(1)); s = empty_state(m)
        p = plan(m, s, {"budget": "2", "max_nodes": 1})
        self.assertEqual(p["status"], "UNKNOWN")
        check_plan(m, s, p, True)
        s = import_observations(m, s, batch(m, [("s0", "old", "1/2"), ("s0", "new", "1/2")]))
        self.assertEqual(envelope(m, s, "0")["decision"], "PASS")
        self.assertEqual(envelope(m, s, "1/100")["decision"], "FAIL")

    def test_checker_rejects_corrupted_bounded_search_metadata(self):
        m = parse_manifest(fixture(1)); s = empty_state(m)
        p = plan(m, s, {"budget": "1", "max_nodes": 1})
        for change in (lambda d: d.update(reduction_upper_bound="-1"),
                       lambda d: d.update(objective="future_scores"), lambda d: d.update(nodes=2),
                       lambda d: d["requirements"].update(max_nodes=0)):
            bad = copy.deepcopy(p); change(bad)
            with self.assertRaises(Error): check_plan(m, s, bad, True)
        no_incumbent = plan(m, s, {"budget": "1", "max_nodes": 1, "coverage": {"main": 1}})
        self.assertEqual(no_incumbent["status"], "UNKNOWN")
        self.assertIsNone(no_incumbent["selected"])
        check_plan(m, s, no_incumbent, True)
        bad = copy.deepcopy(no_incumbent); bad["remaining_width"] = "0"
        with self.assertRaises(Error): check_plan(m, s, bad)

    def test_invalid_schema_and_numbers(self):
        for value in (True, 0.2, "NaN", "1/0", "1e4"):
            with self.assertRaises(Error): number(value)
        for change in (lambda d: d.update(constraints=[]), lambda d: d["items"].append(copy.deepcopy(d["items"][0])),
                       lambda d: d["items"][0]["old"].update(low="2"), lambda d: d["strata"].update(main="1/2")):
            d = fixture(); change(d)
            with self.assertRaises(Error): parse_manifest(d)
        bad = fixture(); bad["version"] = True
        with self.assertRaises(Error): parse_manifest(bad)
        from evalenvelope.cli import read
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp)/"input.json"
            for invalid in ('{"cost":"1","cost":"999"}', '{"value":NaN}'):
                file.write_text(invalid, encoding="utf-8")
                with self.assertRaises(Error): read(file)

    def test_independent_corner_completion_oracle(self):
        # Independently enumerate all endpoint completions, not the formula under test.
        rng = random.Random(8023)
        for trial in range(30):
            raw = fixture(3); raw["strata"] = {"main": "1/3", "rare": "2/3"}
            raw["items"][2]["stratum"] = "rare"
            for row in raw["items"]:
                for arm in ("old", "new"):
                    lo = rng.randrange(-2, 3); hi = lo+rng.randrange(0, 4)
                    row[arm].update(low=str(lo), high=str(hi))
            m = parse_manifest(raw); s = empty_state(m)
            if trial % 2:
                s = import_observations(m, s, batch(m, [("s0", "old", raw["items"][0]["old"]["low"])]))
            cells = [(i, a) for i in m.items for a in ("old", "new")]
            domains = [(s.seen()[i.id, a],) if (i.id, a) in s.seen() else (getattr(i, a).low, getattr(i, a).high) for i, a in cells]
            values = []
            for assignment in product(*domains):
                complete = {(i.id, a): v for (i, a), v in zip(cells, assignment)}
                values.append(sum(i.weight*(complete[i.id, "new"]-complete[i.id, "old"]) for i in m.items))
            certificate = envelope(m, s)
            self.assertEqual((number(certificate["lower"]), number(certificate["upper"])), (min(values), max(values)))
            check_envelope(m, s, certificate)

    def test_independent_subset_plan_oracle(self):
        rng = random.Random(516)
        for trial in range(30):
            raw = fixture(3)
            for row in raw["items"]:
                for arm in ("old", "new"):
                    row[arm]["cost"] = str(rng.randrange(0, 5))
                    row[arm]["high"] = str(rng.randrange(0, 4))
                if trial % 3 == 0: row["bundle_cost"] = "2"
            m = parse_manifest(raw); s = empty_state(m)
            options = {"budget": str(rng.randrange(0, 9)), "coverage": {"main": trial % 3}, "pins": ["s0:new"] if trial % 5 == 0 else []}
            p = plan(m, s, options)
            self.assertNotEqual(p["status"], "UNKNOWN")
            check_plan(m, s, p, True)


if __name__ == "__main__": unittest.main()
