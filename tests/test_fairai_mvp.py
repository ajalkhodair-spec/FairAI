import tempfile
import unittest
from pathlib import Path

from scripts.fairai_mvp import (
    ContentStore,
    EthicalLedger,
    ROUND_ID,
    evaluate,
    generate_partition,
    train_logistic,
)


class FairAIMVPTests(unittest.TestCase):
    def test_content_store_is_content_addressed(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ContentStore(Path(tmp))
            cid1 = store.put_json("artifact.json", {"b": 2, "a": 1})
            cid2 = store.put_json("artifact.json", {"a": 1, "b": 2})
            self.assertEqual(cid1, cid2)
            self.assertEqual(store.get_json(cid1), {"a": 1, "b": 2})

    def test_ledger_rejects_unverified_proof(self):
        ledger = EthicalLedger()
        ledger.register_node(1)
        record = ledger.register_local_model({
            "node_id": 1,
            "round_id": ROUND_ID,
            "cids": {
                "model": "sha256-model",
                "metrics": "sha256-metrics",
                "metadata": "sha256-metadata",
                "proof": "sha256-proof",
                "public": "sha256-public",
            },
            "metrics": {"accuracy": 0.9, "demographic_parity_gap": 0.1},
            "proof_verified": False,
            "zk_public_inputs": {},
        })
        self.assertEqual(record["verification_status"], "Invalid")
        self.assertEqual(record["approval_status"], "Rejected")
        self.assertEqual(ledger.eligible_models(ROUND_ID), [])

    def test_training_produces_reasonable_metrics(self):
        data = generate_partition(1, 80)
        weights = train_logistic(data, epochs=60, learning_rate=0.08)
        metrics = evaluate(weights, data)
        self.assertGreaterEqual(metrics["accuracy"], 0.70)
        self.assertIn("demographic_parity_gap", metrics)


if __name__ == "__main__":
    unittest.main()
