import json
import os
import subprocess
from pathlib import Path

from .b2_infrastructure import B2InfrastructureError, B2KuboLedgerAdapter, _canonical_bytes, _parameters_payload
from .binding import artifact_binding_fields, policy_version_to_uint64
from .policy import evaluate_policy
from .zk_v2 import V2ProofSystem, groth16_contract_proof


ZERO_PROOF = {
    "pA": [0, 0],
    "pB": [[0, 0], [0, 0]],
    "pC": [0, 0],
}


class B4KuboLedgerAdapter(B2KuboLedgerAdapter):
    """Strict full-path adapter for B4 and B7."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proof_system = V2ProofSystem(self.repo_root)
        self.pending = {}
        self.proof_rows = []

    @staticmethod
    def _scaled_metrics(metrics, scale):
        names = (
            "accuracy",
            "demographic_parity_gap",
            "equal_opportunity_gap",
            "equalized_odds_gap",
            "subgroup_accuracy_gap",
        )
        return {
            "schema_version": "fairai.metrics.scaled.v2",
            "scale": scale,
            **{
                name: None if metrics[name] is None else round(metrics[name] * scale)
                for name in names
            },
        }

    @staticmethod
    def _circuit_input(metrics, policy, node_id, round_id, nonce, binding, scale):
        value = lambda name: 0 if metrics[name] is None else int(metrics[name])
        enabled = policy["enabled_metrics"]
        return {
            "accuracy": value("accuracy"),
            "demographicParityGap": value("demographic_parity_gap"),
            "equalOpportunityGap": value("equal_opportunity_gap"),
            "equalizedOddsGap": value("equalized_odds_gap"),
            "subgroupAccuracyGap": value("subgroup_accuracy_gap"),
            "minimumAccuracy": round(policy["minimum_accuracy"] * scale),
            "maximumDemographicParityGap": round(
                policy["maximum_demographic_parity_gap"] * scale
            ),
            "maximumEqualOpportunityGap": round(
                policy["maximum_equal_opportunity_gap"] * scale
            ),
            "maximumEqualizedOddsGap": round(
                policy["maximum_equalized_odds_gap"] * scale
            ),
            "maximumSubgroupAccuracyGap": round(
                policy["maximum_subgroup_accuracy_gap"] * scale
            ),
            "enableAccuracy": int(enabled["accuracy"]),
            "enableDemographicParity": int(enabled["demographic_parity_gap"]),
            "enableEqualOpportunity": int(enabled["equal_opportunity_gap"]),
            "enableEqualizedOdds": int(enabled["equalized_odds_gap"]),
            "enableSubgroupAccuracy": int(enabled["subgroup_accuracy_gap"]),
            "nodeId": node_id,
            "roundId": round_id,
            "policyVersion": policy_version_to_uint64(policy["policy_version"]),
            "nonce": nonce,
            # Circom's JavaScript witness generator parses JSON numbers as IEEE-754.
            # Decimal strings preserve full BN254 field precision.
            "manifestDigestFieldIn": str(binding["manifest_digest_field"]),
            "metricsDigestFieldIn": str(binding["metrics_digest_field"]),
        }

    @staticmethod
    def _expected_public(circuit_input):
        return [int(value) for value in [
            circuit_input["manifestDigestFieldIn"],
            circuit_input["metricsDigestFieldIn"],
            circuit_input["accuracy"],
            circuit_input["demographicParityGap"],
            circuit_input["equalOpportunityGap"],
            circuit_input["equalizedOddsGap"],
            circuit_input["subgroupAccuracyGap"],
            circuit_input["minimumAccuracy"],
            circuit_input["maximumDemographicParityGap"],
            circuit_input["maximumEqualOpportunityGap"],
            circuit_input["maximumEqualizedOddsGap"],
            circuit_input["maximumSubgroupAccuracyGap"],
            circuit_input["enableAccuracy"],
            circuit_input["enableDemographicParity"],
            circuit_input["enableEqualOpportunity"],
            circuit_input["enableEqualizedOdds"],
            circuit_input["enableSubgroupAccuracy"],
            circuit_input["nodeId"],
            circuit_input["roundId"],
            circuit_input["policyVersion"],
            circuit_input["nonce"],
        ]]

    def prepare_round(self, round_id, updates, client_metrics, policy):
        scale = 1_000_000
        submissions = []
        approved_clients = []
        for update in updates:
            if not update.valid or update.client_id not in client_metrics:
                continue
            client_id = update.client_id
            numeric_node_id = int(client_id) + 1
            nonce = round_id * 1_000_000 + numeric_node_id
            prefix = {"round_id": round_id, "node_id": numeric_node_id}
            scaled = self._scaled_metrics(client_metrics[client_id], scale)
            cids = {
                "model": self._publish(
                    round_id,
                    client_id,
                    "model",
                    _canonical_bytes({**prefix, **_parameters_payload(update.parameters)}),
                ),
                "metrics": self._publish(
                    round_id, client_id, "metrics", _canonical_bytes(scaled)
                ),
                "metadata": self._publish(
                    round_id,
                    client_id,
                    "metadata",
                    _canonical_bytes(
                        {
                            **prefix,
                            "method": "B4_or_B7",
                            "sample_count": update.sample_count,
                            "policy_version": policy["policy_version"],
                        }
                    ),
                ),
            }
            bound_manifest = {
                "schema_version": "fairai.bound_manifest.v2",
                **prefix,
                "nonce": nonce,
                "policy_version": policy["policy_version"],
                "artifacts": cids,
            }
            bound_manifest_cid = self._publish(
                round_id,
                client_id,
                "bound_manifest",
                _canonical_bytes(bound_manifest),
            )
            binding = artifact_binding_fields(bound_manifest, scaled)
            circuit_input = self._circuit_input(
                scaled,
                policy,
                numeric_node_id,
                round_id,
                nonce,
                binding,
                scale,
            )
            decision = evaluate_policy(client_metrics[client_id], policy, round_id)
            if decision["approved"]:
                proof_result = self.proof_system.prove(
                    circuit_input,
                    self.output_dir / "proofs" / f"round_{round_id}" / f"client_{client_id}",
                )
                if proof_result["public_signals"] != self._expected_public(circuit_input):
                    raise B2InfrastructureError("V2 public signals do not match bound inputs")
                proof_payload = proof_result["proof"]
                contract_proof = groth16_contract_proof(proof_payload)
                approved_clients.append(client_id)
                self.proof_rows.append(
                    {
                        "round": round_id,
                        "client_id": client_id,
                        "approved": True,
                        "witness_ms": proof_result["witness_ms"],
                        "proof_ms": proof_result["proof_ms"],
                        "verify_ms": proof_result["verify_ms"],
                    }
                )
            else:
                proof_payload = {
                    "status": "not_generated_policy_rejected",
                    "reasons": decision["reasons"],
                }
                contract_proof = ZERO_PROOF
                self.proof_rows.append(
                    {
                        "round": round_id,
                        "client_id": client_id,
                        "approved": False,
                        "witness_ms": 0,
                        "proof_ms": 0,
                        "verify_ms": 0,
                    }
                )
            public_signals = self._expected_public(circuit_input)
            cids["proof"] = self._publish(
                round_id, client_id, "proof", _canonical_bytes(proof_payload)
            )
            cids["public"] = self._publish(
                round_id,
                client_id,
                "public",
                _canonical_bytes({"public_signals": public_signals}),
            )
            submission_manifest = {
                "schema_version": "fairai.submission_manifest.v2",
                **prefix,
                "bound_manifest_cid": bound_manifest_cid,
                "artifacts": cids,
                "approved": decision["approved"],
            }
            cids["manifest"] = self._publish(
                round_id,
                client_id,
                "submission_manifest",
                _canonical_bytes(submission_manifest),
            )
            submissions.append(
                {
                    "node_id": numeric_node_id,
                    "client_id": client_id,
                    "round_id": round_id,
                    "nonce": nonce,
                    "policy_version": policy_version_to_uint64(
                        policy["policy_version"]
                    ),
                    "manifest_hash": binding["manifest_digest"],
                    "metrics_hash": binding["metrics_digest"],
                    "approved": decision["approved"],
                    "groth16_proof": contract_proof,
                    "public_signals": public_signals,
                    "cids": cids,
                }
            )
        self.pending[round_id] = submissions
        return approved_clients

    def record_round(
        self,
        round_id,
        updates,
        client_metrics,
        global_parameters,
        global_metrics,
        included_clients,
    ):
        submissions = self.pending[round_id]
        approved_submissions = [
            item for item in submissions if item["client_id"] in set(included_clients)
        ]
        global_model_cid = self._publish(
            round_id,
            "global",
            "global_model",
            _canonical_bytes(
                {
                    "round_id": round_id,
                    "method": "B4_or_B7",
                    **_parameters_payload(global_parameters),
                }
            ),
        )
        report_cid = self._publish(
            round_id,
            "global",
            "report",
            _canonical_bytes(
                {
                    "schema_version": "fairai.v2_round_report.v1",
                    "round_id": round_id,
                    "global_metrics": global_metrics,
                    "participant_nodes": sorted(included_clients),
                }
            ),
        )
        self.rounds.append(
            {
                "round_id": round_id,
                "submissions": submissions,
                "global_publication": {
                    "global_model_cid": global_model_cid,
                    "report_cid": report_cid,
                    "participant_model_cids": [
                        item["cids"]["model"] for item in approved_submissions
                    ],
                },
            }
        )

    def finalize(self):
        if not self.rounds:
            raise B2InfrastructureError("No B4/B7 rounds were recorded")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        input_path = self.output_dir / "contract_input.json"
        output_path = self.output_dir / "contract_result.json"
        input_path.write_text(
            json.dumps(
                {
                    "schema_version": "fairai.v2_contract_input.v1",
                    "verifier_mode": "v2_groth16_eip712",
                    "rounds": self.rounds,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        completed = subprocess.run(
            ["npx", "hardhat", "run", "scripts/run_v2_rounds.js"],
            cwd=self.repo_root / "hardhat",
            env={
                **os.environ,
                "FAIRAI_CONTRACT_INPUT": str(input_path.resolve()),
                "FAIRAI_CONTRACT_OUTPUT": str(output_path.resolve()),
            },
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if completed.returncode != 0:
            raise B2InfrastructureError("V2 ledger execution failed:\n" + completed.stdout)
        result = json.loads(output_path.read_text(encoding="utf-8"))
        for expected, observed in zip(self.rounds, result["rounds"]):
            expected_cids = sorted(
                item["cids"]["model"]
                for item in expected["submissions"]
                if item["approved"]
            )
            expected_state = "Archived" if expected_cids else "Cancelled"
            if observed["final_state"] != expected_state:
                raise B2InfrastructureError(
                    f"V2 ledger round did not reach {expected_state}"
                )
            if sorted(observed["eligible_model_cids"]) != expected_cids:
                raise B2InfrastructureError("V2 ledger eligibility diverged from proofs")
        result.update(
            {
                "kubo_version": self.kubo_version,
                "publisher_peer_id": self.publisher_id,
                "consumer_peer_id": self.consumer_id,
                "retrieval_rows": self.retrieval_rows,
                "proof_rows": self.proof_rows,
            }
        )
        (self.output_dir / "v2_evidence.json").write_text(
            json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
        )
        return result
