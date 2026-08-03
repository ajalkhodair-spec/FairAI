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

        strict_policy = {
            **policy,
            "minimum_accuracy": 1.0,
            "maximum_demographic_parity_gap": 0.0,
        }
        gated = run_federated_method(
            dataset,
            partition,
            "B3",
            strict_policy,
            "logistic_regression",
            1,
            1,
            12,
            2,
        )
        self.assertEqual(
            gated["round_metrics"][0]["aggregation_status"],
            "skipped_no_eligible_clients",
        )
        self.assertEqual(gated["round_metrics"][0]["included_clients"], 0)

        attacked = run_federated_method(
            dataset,
            partition,
            "B6",
            policy,
            "logistic_regression",
            2,
            2,
            12,
            2,
            attack_type="sign_flip",
            malicious_client_ratio=0.25,
        )
        malicious_ids = {
            row["client_id"]
            for row in attacked["client_metrics"]
            if row["malicious_client"]
        }
        self.assertEqual(len(malicious_ids), 1)
        self.assertTrue(
            all(
                row["attack_type"] == "sign_flip"
                for row in attacked["client_metrics"]
            )
        )

        fairfed = run_federated_method(
            dataset,
            partition,
            "B5",
            policy,
            "logistic_regression",
            2,
            2,
            12,
            2,
            fairfed_beta=1.0,
        )
        self.assertEqual(len(fairfed["round_metrics"]), 2)
        self.assertAlmostEqual(
            sum(fairfed["round_metrics"][0]["fairfed_weights"].values()),
            1.0,
        )

        infrastructure = RecordingInfrastructure()
        b2 = run_federated_method(
            dataset,
            partition,
            "B2",
            policy,
            "logistic_regression",
            2,
            2,
            12,
            2,
            round_infrastructure=infrastructure,
        )
        self.assertEqual(infrastructure.rounds, [1, 2])
        self.assertEqual(b2["infrastructure"]["status"], "recorded")

        full_path = RecordingInfrastructure()
        b7 = run_federated_method(
            dataset,
            partition,
            "B7",
            policy,
            "logistic_regression",
            1,
            2,
            12,
            2,
            round_infrastructure=full_path,
        )
        self.assertEqual(b7["method"], "B7")
        self.assertEqual(full_path.prepared_rounds, [1])


class RecordingInfrastructure:
    def __init__(self):
        self.rounds = []
        self.prepared_rounds = []

    def prepare_round(self, **values):
        self.prepared_rounds.append(values["round_id"])
        return [
            update.client_id
            for update in values["updates"]
            if update.policy_approved
        ]

    def record_round(self, **values):
        self.rounds.append(values["round_id"])
        assert values["included_clients"]
        assert values["client_metrics"]

    def finalize(self):
        return {"status": "recorded"}


if __name__ == "__main__":
    unittest.main()
