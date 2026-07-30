import unittest

import numpy as np

from fairai_revision.data import DatasetSplits, RawSplit
from fairai_revision.federated import run_federated_method
from fairai_revision.partition import partition_clients
from fairai_revision.policy import load_policy_profiles


class RevisionFederatedTests(unittest.TestCase):
    def test_deterministic_two_round_federated_run(self):
        import pandas as pd
        from pathlib import Path

        rng = np.random.default_rng(4)
        size = 240
        frame = pd.DataFrame(
            {
                "x1": rng.normal(size=size),
                "x2": rng.normal(size=size),
            }
        )
        labels = (frame["x1"].to_numpy() + frame["x2"].to_numpy() > 0).astype(int)
        protected = pd.DataFrame(
            {"group": np.where(np.arange(size) % 2, "P", "U")}
        )

        def split(start, end):
            return RawSplit(
                frame.iloc[start:end].reset_index(drop=True),
                labels[start:end],
                protected.iloc[start:end].reset_index(drop=True),
            )

        dataset = DatasetSplits(
            train=split(0, 160),
            validation=split(160, 200),
            test=split(200, 240),
            favorable_label=1,
            primary_protected_attribute="group",
            privileged_value="P",
            unprivileged_value="U",
            metadata={"dataset": "fixture"},
        )
        partition = partition_clients(
            dataset.train.labels,
            dataset.train.protected["group"].to_numpy(),
            client_count=4,
            mode="iid",
            seed=9,
            minimum_samples=30,
        )
        policy = load_policy_profiles(
            Path(__file__).resolve().parents[1]
            / "configs"
            / "revision"
            / "policy_profiles.json"
        )["lenient"]
        first = run_federated_method(
            dataset, partition, "B0", policy, "logistic_regression", 2, 5, 12, 2
        )
        second = run_federated_method(
            dataset, partition, "B0", policy, "logistic_regression", 2, 5, 12, 2
        )
        self.assertEqual(len(first["round_metrics"]), 2)
        self.assertEqual(len(first["client_metrics"]), 8)
        self.assertAlmostEqual(
            first["test_metrics"]["accuracy"],
            second["test_metrics"]["accuracy"],
        )
        for left, right in zip(first["final_parameters"], second["final_parameters"]):
            np.testing.assert_allclose(left, right)


if __name__ == "__main__":
    unittest.main()
