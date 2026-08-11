import unittest
from pathlib import Path

import pandas as pd

from scripts.prepare_results_package import SHEETS


ROOT = Path("outputs/major_revision")
PRIMARY = ROOT / "primary_csv"


class PublicationPackageTests(unittest.TestCase):
    def test_resolved_capabilities_are_backed_by_measured_rows(self):
        readme = pd.read_csv(PRIMARY / "README.csv").set_index("item")["value"]
        for item in ("IPFS status", "V2 proof status", "FairFed status"):
            self.assertNotIn("blocked", readme[item].lower())

        proof = pd.read_csv(PRIMARY / "Proof_Overhead.csv")
        self.assertEqual(set(proof["stage"]), {"witness", "proof", "verification"})
        self.assertTrue((proof["n"] == 30).all())
        self.assertTrue((proof["valid_proofs_verified"] == 30).all())

        ipfs = pd.read_csv(PRIMARY / "IPFS_Add.csv")
        self.assertTrue((ipfs["n"] == 30).all())
        self.assertTrue(ipfs["upload_ms_mean"].notna().all())

        fairfed = pd.read_csv(PRIMARY / "FairFed_Comparison.csv")
        self.assertIn("B5", set(fairfed["method"]))

    def test_current_trust_and_representation_evidence_is_packaged(self):
        trust = pd.read_csv(PRIMARY / "Trust_Boundary.csv")
        self.assertEqual(
            set(trust["scenario"]),
            {"false_metric_reporting", "approved_artifact_unavailable"},
        )
        unavailable = trust.set_index("scenario").loc[
            "approved_artifact_unavailable"
        ]
        self.assertEqual(unavailable["round_state"], "Cancelled")
        self.assertFalse(bool(unavailable["aggregated"]))

        representation = pd.read_csv(PRIMARY / "Representation_Fairness.csv")
        self.assertEqual(
            set(representation["partition"]),
            {"iid", "joint_dirichlet_0.3", "joint_dirichlet_1.0"},
        )

        stages = pd.read_csv(PRIMARY / "Stage_Timing.csv")
        self.assertIn("contract_submission", set(stages["stage"]))
        self.assertIn("approved_model_retrieval", set(stages["stage"]))

    def test_workbook_payload_matches_declared_sheet_contract(self):
        self.assertEqual(len(SHEETS), 43)
        readme = pd.read_csv(PRIMARY / "README.csv").set_index("item")["value"]
        self.assertEqual(
            readme["Figure sheets"],
            "Ten formula-backed result figure sheets; 43 canonical evidence "
            "sheets remain the data source",
        )
        for sheet in (
            "Proof_Overhead",
            "IPFS_Availability",
            "Stage_Timing",
            "Representation_Fairness",
            "Trust_Boundary",
            "Policy_Approval",
            "Paired_Inference",
            "Scaling_Summary",
        ):
            self.assertIn(sheet, SHEETS)

    def test_publication_labels_match_measurement_scope(self):
        matrix = pd.read_csv(PRIMARY / "Experiment_Matrix.csv").set_index(
            "scenario_id"
        )
        for scenario in ("azure_adult_bounded", "azure_compas_bounded"):
            self.assertEqual(
                matrix.loc[scenario, "evidence_type"],
                "configured_not_executed",
            )

        approval = pd.read_csv(PRIMARY / "Policy_Approval.csv")
        final_round = approval[approval["aggregation_scope"] == "final_round"]
        final_means = final_round.set_index("policy_profile")["mean_approval_rate"]
        self.assertAlmostEqual(final_means["lenient"], 0.55)
        self.assertAlmostEqual(final_means["submitted"], 0.42)
        self.assertAlmostEqual(final_means["moderate"], 0.27)
        self.assertAlmostEqual(final_means["strict"], 0.07)

        inference = pd.read_csv(PRIMARY / "Paired_Inference.csv")
        row = inference[
            (inference["analysis_family"] == "core_logistic")
            & (inference["suite"] == "compas_core")
            & (inference["partition"] == "joint_dirichlet_0.3")
            & (inference["comparison"] == "B3-B0")
            & (inference["metric"] == "accuracy")
        ].iloc[0]
        self.assertAlmostEqual(row["paired_effect_size_dz"], -1.448810129248246)
        self.assertAlmostEqual(row["paired_t_p_holm"], 0.03179773136434811)


if __name__ == "__main__":
    unittest.main()
