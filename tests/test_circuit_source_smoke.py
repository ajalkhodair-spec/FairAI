import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CircuitSourceSmokeTests(unittest.TestCase):
    def test_legacy_circuit_contains_expected_public_binding_and_constraints(self):
        source = (ROOT / "circuits" / "FairnessEligibility.circom").read_text(
            encoding="utf-8"
        )
        for signal in (
            "accuracy_in",
            "fairness_gap_in",
            "min_accuracy_in",
            "max_gap_in",
            "node_id_in",
            "round_id_in",
        ):
            self.assertIn(f"signal input {signal};", source)
        self.assertIn("accuracy_ok.out === 1;", source)
        self.assertIn("fairness_ok.out === 1;", source)
        self.assertIn("component main = FairnessEligibility(16);", source)

    def test_v2_circuit_is_versioned_and_binds_required_fields(self):
        source = (ROOT / "circuits" / "FairnessEligibilityV2.circom").read_text(
            encoding="utf-8"
        )
        required = (
            "pragma circom 2.1.6",
            "demographicParityGap",
            "equalOpportunityGap",
            "equalizedOddsGap",
            "subgroupAccuracyGap",
            "enableDemographicParity",
            "nodeId",
            "roundId",
            "policyVersion",
            "nonce",
            "manifestDigestField",
            "metricsDigestField",
        )
        for field in required:
            with self.subTest(field=field):
                self.assertIn(field, source)
        self.assertIn("enabled * (enabled - 1) === 0", source)
        self.assertIn("enabled * (1 - check.out) === 0", source)
        self.assertNotIn("component main = FairnessEligibility(16)", source)


if __name__ == "__main__":
    unittest.main()
