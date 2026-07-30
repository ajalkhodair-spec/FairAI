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


if __name__ == "__main__":
    unittest.main()

