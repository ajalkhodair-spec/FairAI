import copy
import unittest
from pathlib import Path

from fairai_revision.binding import (
    BN254_SCALAR_FIELD,
    BindingError,
    artifact_binding_fields,
    canonical_artifact_bytes,
    digest_to_bn254_field,
    policy_version_to_uint64,
    verify_v2_binding,
)
from fairai_revision.policy import load_policy_profiles


ROOT = Path(__file__).resolve().parents[1]


class RevisionBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_policy_profiles(
            ROOT / "configs" / "revision" / "policy_profiles.json"
        )["submitted"]

    def setUp(self):
        self.metrics = {
            "accuracy": 700,
            "demographic_parity_gap": 100,
            "equal_opportunity_gap": 200,
            "equalized_odds_gap": 200,
            "subgroup_accuracy_gap": 100,
            "scale": 1000,
        }
        self.manifest = {
            "node_id": 7,
            "round_id": 3,
            "policy_version": "1.0.0",
            "nonce": 99,
            "metrics_cid": "bafy-metrics",
        }

    def _inputs(self, manifest=None, metrics=None):
        manifest = manifest or self.manifest
        metrics = metrics or self.metrics
        binding = artifact_binding_fields(manifest, metrics)
        return {
            "accuracy": metrics["accuracy"],
            "demographic_parity_gap": metrics["demographic_parity_gap"],
            "equal_opportunity_gap": metrics["equal_opportunity_gap"],
            "equalized_odds_gap": metrics["equalized_odds_gap"],
            "subgroup_accuracy_gap": metrics["subgroup_accuracy_gap"],
            "minimum_accuracy": 620,
            "maximum_demographic_parity_gap": 280,
            "maximum_equal_opportunity_gap": 1000,
            "maximum_equalized_odds_gap": 1000,
            "maximum_subgroup_accuracy_gap": 1000,
            "enable_accuracy": 1,
            "enable_demographic_parity": 1,
            "enable_equal_opportunity": 0,
            "enable_equalized_odds": 0,
            "enable_subgroup_accuracy": 0,
            "node_id": manifest["node_id"],
            "round_id": manifest["round_id"],
            "policy_version": policy_version_to_uint64(manifest["policy_version"]),
            "nonce": manifest["nonce"],
            "manifest_digest_field": binding["manifest_digest_field"],
            "metrics_digest_field": binding["metrics_digest_field"],
            "proof_generated": True,
        }

    def _verify(self, manifest=None, artifact_metrics=None, public_inputs=None):
        manifest = manifest or self.manifest
        artifact_metrics = artifact_metrics or self.metrics
        inputs = public_inputs or self._inputs()
        return verify_v2_binding(
            manifest,
            artifact_metrics,
            inputs,
            self.policy,
            groth16_verified=True,
        )

    def test_canonical_json_is_order_independent(self):
        left = {"b": [2, 3], "a": 1}
        right = {"a": 1, "b": [2, 3]}
        self.assertEqual(canonical_artifact_bytes(left), canonical_artifact_bytes(right))

    def test_canonical_json_rejects_floats(self):
        with self.assertRaisesRegex(BindingError, "scaled integers"):
            canonical_artifact_bytes({"accuracy": 0.7})

    def test_digest_mapping_is_in_bn254_field(self):
        value = digest_to_bn254_field("ff" * 32)
        self.assertGreaterEqual(value, 0)
        self.assertLess(value, BN254_SCALAR_FIELD)

    def test_policy_version_mapping_is_stable(self):
        self.assertEqual(policy_version_to_uint64("1.2.3"), (1 << 32) | (2 << 16) | 3)
        with self.assertRaises(BindingError):
            policy_version_to_uint64("1.2")

    def test_valid_binding_keeps_security_outcomes_separate(self):
        inputs = self._inputs()
        result = verify_v2_binding(
            self.manifest,
            self.metrics,
            {
                **inputs,
                **artifact_binding_fields(self.manifest, self.metrics),
            },
            self.policy,
            groth16_verified=True,
        )
        self.assertTrue(result["proof_verified"])
        self.assertTrue(result["artifact_binding_valid"])
        self.assertTrue(result["policy_passed"])
        self.assertFalse(result["decision_signed"])

    def test_altered_metric_breaks_binding(self):
        inputs = {
            **self._inputs(),
            **artifact_binding_fields(self.manifest, self.metrics),
        }
        altered = copy.deepcopy(self.metrics)
        altered["accuracy"] = 1000
        result = verify_v2_binding(
            self.manifest, altered, inputs, self.policy, groth16_verified=True
        )
        self.assertFalse(result["artifact_binding_valid"])

    def test_wrong_identity_round_policy_and_nonce_break_binding(self):
        base = {
            **self._inputs(),
            **artifact_binding_fields(self.manifest, self.metrics),
        }
        for field, wrong in (
            ("node_id", 8),
            ("round_id", 4),
            ("policy_version", policy_version_to_uint64("2.0.0")),
            ("nonce", 100),
        ):
            with self.subTest(field=field):
                inputs = {**base, field: wrong}
                result = verify_v2_binding(
                    self.manifest,
                    self.metrics,
                    inputs,
                    self.policy,
                    groth16_verified=True,
                )
                self.assertFalse(result["artifact_binding_valid"])
                self.assertFalse(result["binding_checks"][field])

    def test_altered_threshold_and_mask_break_binding(self):
        base = {
            **self._inputs(),
            **artifact_binding_fields(self.manifest, self.metrics),
        }
        for field, wrong in (
            ("maximum_demographic_parity_gap", 281),
            ("enable_demographic_parity", 0),
        ):
            with self.subTest(field=field):
                result = verify_v2_binding(
                    self.manifest,
                    self.metrics,
                    {**base, field: wrong},
                    self.policy,
                    groth16_verified=True,
                )
                self.assertFalse(result["artifact_binding_valid"])
                self.assertFalse(result["binding_checks"][field])


if __name__ == "__main__":
    unittest.main()
