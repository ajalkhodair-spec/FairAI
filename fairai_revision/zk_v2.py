import hashlib
import json
import subprocess
import time
from pathlib import Path


class ZKV2Error(RuntimeError):
    pass


PUBLIC_SIGNAL_NAMES = (
    "manifestDigestField",
    "metricsDigestField",
    "accuracy",
    "demographicParityGap",
    "equalOpportunityGap",
    "equalizedOddsGap",
    "subgroupAccuracyGap",
    "minimumAccuracy",
    "maximumDemographicParityGap",
    "maximumEqualOpportunityGap",
    "maximumEqualizedOddsGap",
    "maximumSubgroupAccuracyGap",
    "enableAccuracy",
    "enableDemographicParity",
    "enableEqualOpportunity",
    "enableEqualizedOdds",
    "enableSubgroupAccuracy",
    "nodeId",
    "roundId",
    "policyVersion",
    "nonce",
)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class V2ProofSystem:
    def __init__(self, repo_root):
        self.repo_root = Path(repo_root)
        self.artifact_root = self.repo_root / "zk" / "artifacts" / "v2"
        manifest_path = self.artifact_root / "artifact_manifest.json"
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for name, expected in self.manifest["files"].items():
            path = (
                self.repo_root / name
                if name.startswith("hardhat/")
                else self.artifact_root / name
            )
            if not path.is_file() or _sha256(path) != expected:
                raise ZKV2Error(f"V2 artifact checksum mismatch: {name}")
        self.wasm = (
            self.artifact_root
            / "FairnessEligibilityV2_js"
            / "FairnessEligibilityV2.wasm"
        )
        self.witness_generator = (
            self.artifact_root
            / "FairnessEligibilityV2_js"
            / "generate_witness.js"
        )
        self.zkey = self.artifact_root / "FairnessEligibilityV2_final.zkey"
        self.vkey = self.artifact_root / "FairnessEligibilityV2_vkey.json"

    def _run(self, args, expected_success=True):
        started = time.perf_counter()
        completed = subprocess.run(
            args,
            cwd=self.repo_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        succeeded = completed.returncode == 0
        if succeeded != expected_success:
            expectation = "succeed" if expected_success else "fail"
            raise ZKV2Error(
                f"Command was expected to {expectation}: {' '.join(map(str, args))}\n"
                + completed.stdout
            )
        return elapsed_ms, completed.stdout

    def prove(self, circuit_input, output_dir, name="proof"):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        input_path = output_dir / f"{name}_input.json"
        witness_path = output_dir / f"{name}.wtns"
        proof_path = output_dir / f"{name}_proof.json"
        public_path = output_dir / f"{name}_public.json"
        input_path.write_text(
            json.dumps(circuit_input, indent=2, sort_keys=True), encoding="utf-8"
        )
        witness_ms, _ = self._run(
            [
                "node",
                str(self.witness_generator),
                str(self.wasm),
                str(input_path),
                str(witness_path),
            ]
        )
        proof_ms, _ = self._run(
            [
                "snarkjs",
                "groth16",
                "prove",
                str(self.zkey),
                str(witness_path),
                str(proof_path),
                str(public_path),
            ]
        )
        verify_ms, output = self._run(
            [
                "snarkjs",
                "groth16",
                "verify",
                str(self.vkey),
                str(public_path),
                str(proof_path),
            ]
        )
        if "OK!" not in output:
            raise ZKV2Error("snarkjs did not confirm V2 proof verification")
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
        public = json.loads(public_path.read_text(encoding="utf-8"))
        if len(public) != len(PUBLIC_SIGNAL_NAMES):
            raise ZKV2Error("V2 proof returned an unexpected public-signal count")
        return {
            "proof": proof,
            "public_signals": [int(value) for value in public],
            "public_inputs": dict(zip(PUBLIC_SIGNAL_NAMES, map(int, public))),
            "witness_ms": witness_ms,
            "proof_ms": proof_ms,
            "verify_ms": verify_ms,
            "proof_path": str(proof_path),
            "public_path": str(public_path),
        }

    def expect_constraint_failure(self, circuit_input, output_dir, name):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        input_path = output_dir / f"{name}_input.json"
        witness_path = output_dir / f"{name}.wtns"
        input_path.write_text(
            json.dumps(circuit_input, indent=2, sort_keys=True), encoding="utf-8"
        )
        elapsed_ms, output = self._run(
            [
                "node",
                str(self.witness_generator),
                str(self.wasm),
                str(input_path),
                str(witness_path),
            ],
            expected_success=False,
        )
        return {"rejected": True, "runtime_ms": elapsed_ms, "output": output[-2000:]}

    def verify_external(self, proof_path, public_path, expected_success=True):
        elapsed_ms, output = self._run(
            [
                "snarkjs",
                "groth16",
                "verify",
                str(self.vkey),
                str(public_path),
                str(proof_path),
            ],
            expected_success=expected_success,
        )
        return {"verified": expected_success, "runtime_ms": elapsed_ms, "output": output}


def groth16_contract_proof(proof):
    return {
        "pA": [proof["pi_a"][0], proof["pi_a"][1]],
        "pB": [
            [proof["pi_b"][0][1], proof["pi_b"][0][0]],
            [proof["pi_b"][1][1], proof["pi_b"][1][0]],
        ],
        "pC": [proof["pi_c"][0], proof["pi_c"][1]],
    }
