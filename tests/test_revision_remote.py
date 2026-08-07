import tempfile
import unittest
from pathlib import Path

import numpy as np

from fairai_revision.remote import (
    RemoteTrainingError,
    balanced_client_assignment,
    validate_remote_topology,
)
from fairai_revision.remote_worker import execute_training_request


class RevisionRemoteTests(unittest.TestCase):
    def test_remote_topology_validation_is_fail_closed(self):
        valid = {
            "schema_version": "fairai.azure_topology.v1",
            "ssh_user": "fairaiadmin",
            "ssh_key": "/tmp/test-key",
            "kubo_publisher_api": "http://10.42.0.5:5001",
            "kubo_consumer_api": "http://10.42.0.6:5001",
            "workers": [
                {"name": "worker1", "host": "10.42.0.5"},
                {"name": "worker2", "host": "10.42.0.6"},
            ],
        }
        self.assertIs(validate_remote_topology(valid), valid)
        with self.assertRaises(RemoteTrainingError):
            validate_remote_topology({**valid, "workers": [valid["workers"][0]]})
        with self.assertRaises(RemoteTrainingError):
            validate_remote_topology(
                {**valid, "kubo_consumer_api": valid["kubo_publisher_api"]}
            )
        with self.assertRaises(RemoteTrainingError):
            validate_remote_topology(
                {
                    **valid,
                    "workers": [
                        valid["workers"][0],
                        {"name": "worker1", "host": "bad host"},
                    ],
                }
            )

    def test_balanced_assignment_is_deterministic(self):
        self.assertEqual(
            balanced_client_assignment(5, ["worker1", "worker2"]),
            {"0": "worker1", "1": "worker2", "2": "worker1", "3": "worker2", "4": "worker1"},
        )
        with self.assertRaises(RemoteTrainingError):
            balanced_client_assignment(5, ["only-one-worker"])

    def test_staged_worker_trains_without_network_access(self):
        rng = np.random.default_rng(17)
        train = rng.normal(size=(80, 3))
        train_labels = (train[:, 0] + train[:, 1] > 0).astype(int)
        evaluation = rng.normal(size=(40, 3))
        evaluation_labels = (evaluation[:, 0] + evaluation[:, 1] > 0).astype(int)
        protected = np.where(np.arange(40) % 2, "P", "U")
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "client.npz"
            np.savez_compressed(
                bundle,
                train_features=train,
                train_labels=train_labels,
                evaluation_features=evaluation,
                evaluation_labels=evaluation_labels,
                evaluation_protected=protected,
            )
            result = execute_training_request(
                bundle,
                {
                    "model_type": "logistic_regression",
                    "seed": 2,
                    "local_epochs": 3,
                    "global_parameters": [np.zeros((1, 3)).tolist(), [0.0]],
                    "privileged_value": "P",
                    "unprivileged_value": "U",
                    "favorable_label": 1,
                    "minimum_group_samples": 2,
                    "label_flip": False,
                },
            )
            evaluated = execute_training_request(
                bundle,
                {
                    "operation": "evaluate",
                    "model_type": "logistic_regression",
                    "seed": 2,
                    "local_epochs": 0,
                    "global_parameters": [np.zeros((1, 3)).tolist(), [0.0]],
                    "privileged_value": "P",
                    "unprivileged_value": "U",
                    "favorable_label": 1,
                    "minimum_group_samples": 2,
                    "label_flip": False,
                },
            )
        self.assertEqual(len(result["parameters"]), 2)
        self.assertGreater(result["metrics"]["accuracy"], 0.5)
        self.assertGreater(result["worker_runtime_ms"], 0)
        np.testing.assert_allclose(evaluated["parameters"][0], np.zeros((1, 3)))


if __name__ == "__main__":
    unittest.main()
