import json
import tempfile
import unittest
from pathlib import Path

from fairai_revision.config import ConfigError, config_hash, load_config, validate_config
from fairai_revision.manifest import validate_manifest
from fairai_revision.run import (
    baseline_comparison,
    display_output_dir,
    execute,
    experiment_seeds,
)


ROOT = Path(__file__).resolve().parents[1]


class RevisionInfrastructureTests(unittest.TestCase):
    def test_v2_digest_inputs_preserve_bn254_precision(self):
        from fairai_revision.b4_infrastructure import B4KuboLedgerAdapter
        from fairai_revision.binding import artifact_binding_fields

        large_manifest = 2**200 + 12345
        large_metrics = 2**199 + 67890
        metrics = {
            "accuracy": 800000,
            "demographic_parity_gap": 100000,
            "equal_opportunity_gap": 90000,
            "equalized_odds_gap": 120000,
            "subgroup_accuracy_gap": 80000,
        }
        policy = {
            "policy_version": "1.0.0",
            "minimum_accuracy": 0.62,
            "maximum_demographic_parity_gap": 0.28,
            "maximum_equal_opportunity_gap": 0.28,
            "maximum_equalized_odds_gap": 0.28,
            "maximum_subgroup_accuracy_gap": 0.28,
            "enabled_metrics": {
                "accuracy": True,
                "demographic_parity_gap": True,
                "equal_opportunity_gap": True,
                "equalized_odds_gap": True,
                "subgroup_accuracy_gap": True,
            },
        }
        circuit_input = B4KuboLedgerAdapter._circuit_input(
            metrics,
            policy,
            node_id=1,
            round_id=1,
            nonce=1,
            binding={
                "manifest_digest_field": large_manifest,
                "metrics_digest_field": large_metrics,
            },
            scale=1_000_000,
        )
        self.assertEqual(circuit_input["manifestDigestFieldIn"], str(large_manifest))
        self.assertEqual(circuit_input["metricsDigestFieldIn"], str(large_metrics))
        public = B4KuboLedgerAdapter._expected_public(circuit_input)
        self.assertEqual(public[:2], [large_manifest, large_metrics])
        serialized = B4KuboLedgerAdapter._serialized_public(public)
        self.assertEqual(serialized[:2], [str(large_manifest), str(large_metrics)])
        self.assertTrue(all(isinstance(value, str) for value in serialized))
        manifest = {
            "node_id": 1,
            "round_id": 1,
            "nonce": 1,
            "policy_version": "1.0.0",
        }
        first = artifact_binding_fields(manifest, {"round_id": 1, **metrics})
        second = artifact_binding_fields(manifest, {"round_id": 2, **metrics})
        self.assertNotEqual(first["metrics_digest"], second["metrics_digest"])

    def test_experiment_seed_validation(self):
        self.assertEqual(
            experiment_seeds({"seed": 1, "experiment_seeds": [2, 3]}),
            [2, 3],
        )
        with self.assertRaisesRegex(ValueError, "unique"):
            experiment_seeds({"seed": 1, "experiment_seeds": [2, 2]})
        with self.assertRaises(ValueError):
            experiment_seeds({"seed": 1, "experiment_seeds": []})

    def test_scaling_config_declares_measured_and_blocked_methods(self):
        config = load_config(ROOT / "configs" / "revision" / "scaling.yaml")
        self.assertEqual(config["executor"], "federated_core")
        self.assertEqual(config["client_counts"], [3, 5, 10, 20, 50])
        self.assertEqual(config["executable_methods"], ["B0", "B2", "B4"])
        self.assertEqual(config["methods_not_executed"], {})

    def test_config_hash_is_canonical(self):
        first = {"b": 2, "a": 1}
        second = {"a": 1, "b": 2}
        self.assertEqual(config_hash(first), config_hash(second))

    def test_required_config_fields_are_enforced(self):
        with self.assertRaises(ConfigError):
            validate_config({"schema_version": "fairai.revision.config.v1"})

    def test_all_revision_configs_are_valid(self):
        for path in sorted((ROOT / "configs" / "revision").glob("*.yaml")):
            with self.subTest(path=path.name):
                load_config(path)

    def test_manifest_validation_rejects_missing_fields(self):
        with self.assertRaises(ValueError):
            validate_manifest({"schema_version": "fairai.revision.run_manifest.v1"})

    def test_smoke_run_is_traceable_and_resumable(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir, manifest = execute(
                ROOT / "configs" / "revision" / "smoke.yaml",
                tmp,
                run_id="test-smoke",
            )
            self.assertEqual(manifest["completion_status"], "completed")
            self.assertTrue(manifest["configuration_hash"])
            self.assertTrue(manifest["dataset_checksum"])
            self.assertTrue((output_dir / "metrics" / "client_1.json").is_file())

            resumed_dir, resumed = execute(
                ROOT / "configs" / "revision" / "smoke.yaml",
                tmp,
                run_id="test-smoke",
                resume=True,
            )
            self.assertEqual(resumed_dir, output_dir)
            self.assertEqual(resumed["completion_status"], "completed")

    def test_external_output_root_has_a_printable_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            external = Path(tmp) / "result"
            self.assertEqual(display_output_dir(external), str(external.resolve()))

    def test_baseline_comparison_uses_configured_tolerance(self):
        config = {
            "numeric_tolerance": 0.0001,
            "expected_baseline": {
                "nodes": {
                    "1": {"accuracy": 0.95, "demographic_parity_gap": 0.01}
                },
                "approved_nodes": 1,
                "rejected_nodes": 0,
                "global_accuracy": 0.9,
                "global_demographic_parity_gap": 0.1,
                "approval_rate": 1.0,
                "global_publication_gas": 100,
            },
        }
        node_rows = [
            {
                "trial": 1,
                "node_id": 1,
                "accuracy": 0.95005,
                "demographic_parity_gap": 0.01005,
            }
        ]
        global_rows = [
            {
                "trial": 1,
                "approved_nodes": 1,
                "rejected_nodes": 0,
                "global_accuracy": 0.90005,
                "global_demographic_parity_gap": 0.10005,
                "approval_rate": 1.0,
            }
        ]
        gas_rows = [
            {
                "trial": 1,
                "operation": "global_publication",
                "gas_used": 100,
            }
        ]
        result = baseline_comparison(config, node_rows, global_rows, gas_rows)
        self.assertTrue(result["all_matched"])


if __name__ == "__main__":
    unittest.main()
