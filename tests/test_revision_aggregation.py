import unittest

import numpy as np

from fairai_revision.aggregation import (
    BASELINE_SPECS,
    AggregationError,
    ClientUpdate,
    aggregate_for_method,
    coordinate_median,
    fedavg,
)


def update(client_id, value, samples=1, **status):
    return ClientUpdate(
        client_id=client_id,
        parameters=(np.asarray([value], dtype=float), np.asarray([[value, value]])),
        sample_count=samples,
        **status,
    )


class RevisionAggregationTests(unittest.TestCase):
    def test_weighted_fedavg(self):
        result = fedavg([update("a", 1, samples=1), update("b", 3, samples=3)])
        np.testing.assert_allclose(result[0], [2.5])
        np.testing.assert_allclose(result[1], [[2.5, 2.5]])

    def test_coordinate_median_rejects_outlier_influence(self):
        result = coordinate_median(
            [update("a", 1), update("b", 2), update("attacker", 1000)]
        )
        np.testing.assert_allclose(result[0], [2])
        np.testing.assert_allclose(result[1], [[2, 2]])

    def test_baseline_selection_semantics(self):
        updates = [
            update(
                "approved",
                1,
                policy_approved=True,
                proof_verified=True,
                artifact_binding_valid=True,
                decision_signed=True,
                on_chain_approved=True,
            ),
            update(
                "policy_only",
                3,
                policy_approved=True,
                proof_verified=False,
                artifact_binding_valid=False,
                decision_signed=False,
                on_chain_approved=False,
            ),
            update("rejected", 9, policy_approved=False),
        ]
        self.assertEqual(
            aggregate_for_method("B0", updates)["included_clients"],
            ["approved", "policy_only", "rejected"],
        )
        self.assertEqual(
            aggregate_for_method("B3", updates)["included_clients"],
            ["approved", "policy_only"],
        )
        full = aggregate_for_method("B4", updates)
        self.assertEqual(full["included_clients"], ["approved"])
        self.assertIn("proof_verified", full["excluded_clients"]["policy_only"])

    def test_b7_gates_then_uses_coordinate_median(self):
        approved_status = {
            "policy_approved": True,
            "proof_verified": True,
            "artifact_binding_valid": True,
            "decision_signed": True,
            "on_chain_approved": True,
        }
        result = aggregate_for_method(
            "B7",
            [
                update("a", 1, **approved_status),
                update("b", 2, **approved_status),
                update("c", 1000, **approved_status),
                update("blocked", -1000, policy_approved=False),
            ],
        )
        np.testing.assert_allclose(result["parameters"][0], [2])
        self.assertEqual(result["included_clients"], ["a", "b", "c"])

    def test_empty_approved_set_fails_explicitly(self):
        with self.assertRaisesRegex(AggregationError, "empty"):
            aggregate_for_method("B3", [update("a", 1, policy_approved=False)])

    def test_invalid_shapes_and_nonfinite_values_fail(self):
        with self.assertRaises(AggregationError):
            fedavg(
                [
                    update("a", 1),
                    ClientUpdate("b", (np.asarray([1, 2]),), 1),
                ]
            )
        with self.assertRaises(AggregationError):
            fedavg([update("a", np.nan)])

    def test_fairfed_is_not_substituted_with_a_custom_heuristic(self):
        with self.assertRaisesRegex(AggregationError, "primary-paper"):
            aggregate_for_method("B5", [update("a", 1)])

    def test_required_baseline_registry_is_explicit(self):
        self.assertEqual(set(BASELINE_SPECS), {"B0", "B1", "B2", "B3", "B4", "B6", "B7"})
        self.assertFalse(BASELINE_SPECS["B0"].blockchain)
        self.assertTrue(BASELINE_SPECS["B4"].groth16)
        self.assertEqual(BASELINE_SPECS["B6"].aggregation, "coordinate_median")


if __name__ == "__main__":
    unittest.main()
