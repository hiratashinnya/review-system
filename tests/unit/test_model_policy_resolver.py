"""モデル実行なしで系統・層と数値版選択の契約を検査する。"""

import copy
import unittest

from model_policy.policy import load_policy, validate_policy
from model_policy.resolver import model_version, resolve_models


def candidate(selector, minor="", major=None):
    version = str(selector["major"] if major is None else major)
    suffix = "-" + selector["suffix"] if selector["suffix"] else ""
    return selector["prefix"] + "-" + version + minor + suffix


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy()
        self.families = self.policy["platforms"]["codex"]["families"]

    def test_numeric_latest_is_order_independent_and_tier_specific(self):
        models = [{"id": candidate(selector, minor)}
                  for selector in self.families.values()
                  for minor in (".2", ".10", "", ".10.1")]
        expected = {tier: candidate(self.families[family], ".10.1")
                    for tier, family in self.policy["platforms"]["codex"]["tiers"].items()}
        self.assertEqual(resolve_models(self.policy, "codex", models), expected)
        self.assertEqual(resolve_models(self.policy, "codex", list(reversed(models))), expected)

    def test_major_crossing_missing_tier_and_invalid_ids_stop(self):
        for models in ([], [{"id": candidate(s, major=s["major"] + 1)}
                            for s in self.families.values()],
                       [{"id": candidate(next(iter(self.families.values())))}],
                       [{"id": None}]):
            with self.subTest(models=models), self.assertRaises(ValueError):
                resolve_models(self.policy, "codex", models)

    def test_aliases_do_not_select_and_equal_numeric_versions_stop(self):
        selector = next(iter(self.families.values()))
        self.assertIsNone(model_version(candidate(selector, ".1-preview"), selector))
        self.assertEqual(model_version(candidate(selector), selector), ())
        models = [{"id": candidate(s, minor)} for s in self.families.values()
                  for minor in (".1", ".1.0")]
        with self.assertRaises(ValueError):
            resolve_models(self.policy, "codex", models)

    def test_copilot_separator_uses_same_numeric_rule(self):
        config = self.policy["platforms"]["copilot"]
        models = [{"id": candidate(s, "-10")} for s in config["families"].values()]
        self.assertEqual(resolve_models(self.policy, "copilot", models),
                         {tier: candidate(config["families"][family], "-10")
                          for tier, family in config["tiers"].items()})

    def test_schema_rejects_pins_missing_tiers_and_invalid_shapes(self):
        mutations = (
            lambda p: p["platforms"]["codex"].update({"minor": 1}),
            lambda p: p["platforms"]["codex"]["tiers"].pop("top"),
            lambda p: p["platforms"]["codex"]["families"].clear(),
            lambda p: p["platforms"]["codex"]["budgets"].update({"最大": "low"}),
            lambda p: p["copilot_agents"].update({"bad/name": "mid"}),
            lambda p: next(iter(p["platforms"]["codex"]["families"].values())).update({"minor": 1}),
        )
        for mutate in mutations:
            policy = copy.deepcopy(self.policy)
            mutate(policy)
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                validate_policy(policy)
