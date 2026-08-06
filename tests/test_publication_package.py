import json
import unittest
from pathlib import Path

import pandas as pd


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
        payload = json.loads((ROOT / "workbook_payload.json").read_text())
        self.assertEqual(len(payload["sheets"]), 40)
        for sheet in (
            "Proof_Overhead",
            "IPFS_Availability",
            "Stage_Timing",
            "Representation_Fairness",
            "Trust_Boundary",
        ):
            self.assertIn(sheet, payload["sheets"])


if __name__ == "__main__":
    unittest.main()
