import json
import tempfile
import unittest
from pathlib import Path

from fairai_revision.config import ConfigError, config_hash, load_config, validate_config
from fairai_revision.manifest import validate_manifest
from fairai_revision.run import execute


ROOT = Path(__file__).resolve().parents[1]


class RevisionInfrastructureTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

