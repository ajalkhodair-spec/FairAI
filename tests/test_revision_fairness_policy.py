import copy
import unittest
from pathlib import Path

import numpy as np

from fairai_revision.fairness import FairnessMetricError, evaluate_group_fairness
from fairai_revision.policy import (
    PolicyError,
    evaluate_policy,
    load_policy_profiles,
    validate_policy,
)


ROOT = Path(__file__).resolve().parents[1]


class RevisionFairnessTests(unittest.TestCase):
    def test_manually_verifiable_binary_group_metrics(self):
        y_true = np.array([1, 1, 0, 0, 1, 1, 0, 0])
        y_pred = np.array([1, 0, 1, 0, 1, 1, 0, 0])
        protected = np.array(["U"] * 4 + ["P"] * 4)
        result = evaluate_group_fairness(
            y_true,
            y_pred,
            protected,
            privileged_value="P",
            unprivileged_value="U",
            minimum_group_samples=2,
        )
        self.assertAlmostEqual(result["accuracy"], 0.75)
        self.assertAlmostEqual(result["demographic_parity_gap"], 0.0)
        self.assertAlmostEqual(result["equal_opportunity_gap"], 0.5)
        self.assertAlmostEqual(result["equalized_odds_gap"], 0.5)
        self.assertAlmostEqual(result["subgroup_accuracy_gap"], 0.5)
        self.assertAlmostEqual(
            result["groups"]["U"]["false_negative_rate"]["value"], 0.5
        )
        self.assertAlmostEqual(
            result["groups"]["P"]["true_negative_rate"]["value"], 1.0
        )

    def test_undefined_metric_is_none_with_reason(self):
        result = evaluate_group_fairness(
            [1, 1, 0, 0],
            [1, 0, 1, 0],
            ["U", "U", "P", "P"],
            privileged_value="P",
            unprivileged_value="U",
        )
        self.assertIsNone(result["equal_opportunity_gap"])
        self.assertIsNone(result["equalized_odds_gap"])
        self.assertIn("equal_opportunity_gap", result["undefined_metrics"])
        self.assertIsNotNone(result["demographic_parity_gap"])

    def test_minimum_group_size_makes_comparison_gaps_undefined(self):
        result = evaluate_group_fairness(
            [1, 0, 1, 0],
            [1, 0, 1, 0],
            ["U", "U", "P", "P"],
            privileged_value="P",
            unprivileged_value="U",
            minimum_group_samples=3,
        )
        self.assertIsNone(result["demographic_parity_gap"])
        self.assertIn("comparison_groups", result["undefined_metrics"])

    def test_invalid_inputs_fail(self):
        with self.assertRaises(FairnessMetricError):
            evaluate_group_fairness(
                [], [], [], privileged_value="P", unprivileged_value="U"
            )


class RevisionPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = load_policy_profiles(
            ROOT / "configs" / "revision" / "policy_profiles.json"
        )

    def test_required_profiles_are_valid(self):
        self.assertEqual(
            set(self.profiles),
            {"lenient", "submitted", "moderate", "strict", "multi_metric"},
        )
        for profile in self.profiles.values():
            validate_policy(profile)

    def test_submitted_policy_preserves_thresholds_and_and_semantics(self):
        policy = self.profiles["submitted"]
        approved = evaluate_policy(
            {
                "accuracy": 0.62,
                "demographic_parity_gap": 0.28,
            },
            policy,
            round_id=1,
        )
        rejected = evaluate_policy(
            {
                "accuracy": 0.90,
                "demographic_parity_gap": 0.281,
            },
            policy,
            round_id=1,
        )
        self.assertTrue(approved["approved"])
        self.assertFalse(rejected["approved"])

    def test_undefined_enabled_metric_rejects_by_default(self):
        decision = evaluate_policy(
            {
                "accuracy": 0.90,
                "demographic_parity_gap": None,
            },
            self.profiles["submitted"],
            round_id=1,
        )
        self.assertFalse(decision["approved"])
        self.assertIn("undefined", decision["reasons"][0])

    def test_policy_round_range_is_enforced(self):
        decision = evaluate_policy(
            {
                "accuracy": 1.0,
                "demographic_parity_gap": 0.0,
            },
            self.profiles["submitted"],
            round_id=1000001,
        )
        self.assertFalse(decision["approved"])
        self.assertIn("not valid", decision["reasons"][0])

    def test_undefined_error_behavior_raises(self):
        policy = copy.deepcopy(self.profiles["submitted"])
        policy["undefined_metric_behavior"] = "error"
        with self.assertRaises(PolicyError):
            evaluate_policy(
                {"accuracy": 0.9, "demographic_parity_gap": None},
                policy,
                round_id=1,
            )


if __name__ == "__main__":
    unittest.main()
