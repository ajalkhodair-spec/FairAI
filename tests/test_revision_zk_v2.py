import json
import tempfile
import unittest
from pathlib import Path

from fairai_revision.zk_v2 import V2ProofSystem


ROOT = Path(__file__).resolve().parents[1]


class RevisionZKV2Tests(unittest.TestCase):
    def test_packaged_artifacts_generate_and_verify_a_real_proof(self):
        system = V2ProofSystem(ROOT)
        circuit_input = json.loads(
            (ROOT / "tests" / "fixtures" / "v2_valid_input.json").read_text(
                encoding="utf-8"
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = system.prove(circuit_input, tmp)
        self.assertEqual(result["public_inputs"]["nodeId"], 1)
        self.assertEqual(result["public_inputs"]["roundId"], 1)
        self.assertEqual(result["public_inputs"]["manifestDigestField"], 123)
        self.assertGreater(result["proof_ms"], 0)


if __name__ == "__main__":
    unittest.main()
