import unittest

import numpy as np
import pandas as pd

from fairai_revision.statistics import _holm_adjust, paired_b3_vs_b0, summarize


class RevisionStatisticsTests(unittest.TestCase):
    def test_summary_and_paired_statistics(self):
        rows = []
        for seed, b0, b3 in ((1, 0.7, 0.6), (2, 0.8, 0.7), (3, 0.9, 0.8)):
            for method, accuracy in (("B0", b0), ("B3", b3)):
                rows.append(
                    {
                        "scenario_id": "fixture",
                        "seed": seed,
                        "partition": "iid",
                        "method": method,
                        "accuracy": accuracy,
                        "macro_f1": accuracy,
                        "demographic_parity_gap": 0.1,
                        "equal_opportunity_gap": 0.1,
                        "equalized_odds_gap": 0.1,
                        "subgroup_accuracy_gap": 0.1,
                        "runtime_ms": 1.0,
                    }
                )
        frame = pd.DataFrame(rows)
        summaries = summarize(frame)
        accuracy = next(
            row
            for row in summaries
            if row["method"] == "B0" and row["metric"] == "accuracy"
        )
        self.assertEqual(accuracy["n"], 3)
        self.assertAlmostEqual(accuracy["mean"], 0.8)
        paired = paired_b3_vs_b0(frame)
        difference = next(row for row in paired if row["metric"] == "accuracy")
        self.assertAlmostEqual(difference["mean_difference"], -0.1)
        self.assertEqual(difference["n"], 3)

    def test_holm_adjustment_is_monotonic_and_bounded(self):
        adjusted = _holm_adjust([0.01, 0.04, 0.03])
        self.assertTrue(np.all((adjusted >= 0) & (adjusted <= 1)))
        order = np.argsort([0.01, 0.04, 0.03])
        self.assertTrue(np.all(np.diff(adjusted[order]) >= 0))


if __name__ == "__main__":
    unittest.main()
