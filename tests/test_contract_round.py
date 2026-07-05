import tempfile
import unittest
from pathlib import Path

from scripts.fairai_mvp import ROUND_ID, sha256_bytes, stable_json, run_contract_round


def proof_fields(node_id, approved):
    proof_payload = {"node_id": node_id, "approved": approved}
    proof_bytes = stable_json(proof_payload)
    return {
        "contract_proof": proof_bytes.hex(),
        "contract_public_signals": [
            str(950),
            str(10 if approved else 290),
            str(620),
            str(280),
            str(76),
            str(80),
            str(20),
            str(40),
            str(21 if approved else 31),
            str(40),
            str(node_id),
            str(ROUND_ID),
            str(int(sha256_bytes(proof_bytes), 16)),
        ],
    }


class ContractRoundIntegrationTests(unittest.TestCase):
    def test_contract_round_returns_only_approved_model_cids(self):
        submissions = [
            {
                "node_id": 1,
                "round_id": ROUND_ID,
                "cids": {
                    "model": "sha256-model-1",
                    "proof": "sha256-proof-1",
                    "public": "sha256-public-1",
                    "metadata": "sha256-metadata-1",
                    "metrics": "sha256-metrics-1",
                    "manifest": "sha256-manifest-1",
                },
                "proof_verified": True,
                **proof_fields(1, True),
            },
            {
                "node_id": 2,
                "round_id": ROUND_ID,
                "cids": {
                    "model": "sha256-model-2",
                    "proof": "sha256-proof-2",
                    "public": "sha256-public-2",
                    "metadata": "sha256-metadata-2",
                    "metrics": "sha256-metrics-2",
                    "manifest": "sha256-manifest-2",
                },
                "proof_verified": False,
                **proof_fields(2, False),
            },
        ]

        with tempfile.TemporaryDirectory() as tmp:
            result = run_contract_round(Path(tmp), submissions, {
                "global_model_cid": "sha256-global-1",
                "report_cid": "sha256-report-1",
                "participant_model_cids": ["sha256-model-1"],
            }, verifier_mode="mock")

        self.assertEqual(result["network"], "hardhat")
        self.assertEqual(result["eligible_model_cids"], ["sha256-model-1"])
        self.assertEqual(result["records"][0]["approval_status"], "Approved")
        self.assertEqual(result["records"][1]["approval_status"], "Rejected")
        self.assertEqual(result["records"][0]["manifest_cid"], "sha256-manifest-1")
        self.assertEqual(result["global_publication"]["global_model_cid"], "sha256-global-1")
        self.assertEqual(result["final_round_state"], "Archived")
        self.assertEqual(
            [event["state"] for event in result["round_events"]],
            ["Open", "SubmissionClosed", "AggregationStarted", "Published", "Archived"],
        )
        self.assertEqual(len(result["audit_events"]), 2)


if __name__ == "__main__":
    unittest.main()
