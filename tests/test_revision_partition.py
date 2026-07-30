import csv
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from fairai_revision.partition import (
    PartitionError,
    entropy_records,
    export_partition_evidence,
    normalized_entropy,
    parse_partition_spec,
    partition_clients,
    source_entropy,
)


class RevisionPartitionTests(unittest.TestCase):
    def setUp(self):
        self.labels = np.tile([0, 1], 200)
        self.protected = np.tile(["A", "A", "B", "B"], 100)

    def test_iid_partition_is_reproducible_and_complete(self):
        first = partition_clients(
            self.labels, self.protected, 10, "iid", seed=17, minimum_samples=30
        )
        second = partition_clients(
            self.labels, self.protected, 10, "iid", seed=17, minimum_samples=30
        )
        self.assertEqual(first.checksum, second.checksum)
        self.assertEqual([len(part) for part in first.client_indices], [40] * 10)
        flat = np.concatenate(first.client_indices)
        self.assertEqual(len(np.unique(flat)), len(self.labels))

    def test_partition_spec_parser(self):
        self.assertEqual(parse_partition_spec("iid"), ("iid", None))
        self.assertEqual(
            parse_partition_spec("label_dirichlet_0.3"),
            ("label_dirichlet", 0.3),
        )
        self.assertEqual(
            parse_partition_spec("joint_dirichlet_1.0"),
            ("joint_dirichlet", 1.0),
        )
        with self.assertRaises(PartitionError):
            parse_partition_spec("joint_dirichlet_zero")

    def test_dirichlet_modes_are_reproducible_and_respect_minimum(self):
        for mode in ("label_dirichlet", "joint_dirichlet"):
            with self.subTest(mode=mode):
                first = partition_clients(
                    self.labels,
                    self.protected,
                    8,
                    mode,
                    seed=29,
                    alpha=0.3,
                    minimum_samples=10,
                )
                second = partition_clients(
                    self.labels,
                    self.protected,
                    8,
                    mode,
                    seed=29,
                    alpha=0.3,
                    minimum_samples=10,
                )
                self.assertEqual(first.checksum, second.checksum)
                self.assertTrue(all(len(part) >= 10 for part in first.client_indices))

    def test_impossible_minimum_fails_explicitly(self):
        with self.assertRaisesRegex(PartitionError, "cannot satisfy"):
            partition_clients(
                self.labels, self.protected, 9, "iid", seed=1, minimum_samples=45
            )

    def test_normalized_entropy_formulas(self):
        self.assertAlmostEqual(normalized_entropy([0, 0, 1, 1]), 1.0)
        self.assertAlmostEqual(normalized_entropy([0, 0, 0, 0], [0, 1]), 0.0)
        expected = -(0.75 * math.log(0.75) + 0.25 * math.log(0.25)) / math.log(2)
        self.assertAlmostEqual(normalized_entropy([0, 0, 0, 1], [0, 1]), expected)
        self.assertAlmostEqual(
            source_entropy((np.arange(2), np.arange(2, 4))), 1.0
        )

    def test_entropy_records_include_distributions(self):
        result = partition_clients(
            self.labels, self.protected, 4, "iid", seed=3, minimum_samples=50
        )
        records = entropy_records(result, self.labels, self.protected)
        self.assertEqual(len(records), 4)
        self.assertEqual(sum(record["sample_count"] for record in records), 400)
        self.assertIn("joint_distribution", records[0])

    def test_evidence_export_marks_unavailable_correlations_undefined(self):
        result = partition_clients(
            self.labels, self.protected, 4, "iid", seed=3, minimum_samples=50
        )
        with tempfile.TemporaryDirectory() as directory:
            summary = export_partition_evidence(
                directory, result, self.labels, self.protected
            )
            expected = {
                "entropy_by_client.csv",
                "entropy_summary.csv",
                "entropy_correlations.csv",
                "partition_summary.csv",
            }
            self.assertEqual(set(summary["files"]), expected)
            with (Path(directory) / "entropy_correlations.csv").open(
                encoding="utf-8"
            ) as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 10)
            self.assertTrue(all(row["status"] == "undefined" for row in rows))


if __name__ == "__main__":
    unittest.main()
