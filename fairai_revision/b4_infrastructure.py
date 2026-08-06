import json
import time
from pathlib import Path

import numpy as np

from .b2_infrastructure import B2InfrastructureError, B2KuboLedgerAdapter, _canonical_bytes, _parameters_payload
from .binding import artifact_binding_fields, policy_version_to_uint64
from .ledger_bridge import HardhatV2LedgerBridge, LedgerBridgeError
from .policy import evaluate_policy
from .zk_v2 import V2ProofSystem, groth16_contract_proof


ZERO_PROOF = {
    "pA": [0, 0],
    "pB": [[0, 0], [0, 0]],
    "pC": [0, 0],
}


class ApprovedArtifactUnavailable(B2InfrastructureError):
    def __init__(self, message, cancellation):
        super().__init__(message)
        self.cancellation = cancellation


class B4KuboLedgerAdapter(B2KuboLedgerAdapter):
    """Strict full-path adapter for B4 and B7."""

    def __init__(
        self, *args, fault_injection=None, metric_integrity_experiment=None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.proof_system = V2ProofSystem(self.repo_root)
        self.pending = {}
        self.proof_rows = []
        self.bridge = HardhatV2LedgerBridge(self.repo_root, self.output_dir)
        self.protocol_commands = []
        self.fault_injection = fault_injection
        self.fault_injection_rows = []
        self.metric_integrity_experiment = metric_integrity_experiment
        self.metric_integrity_rows = []

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

    @staticmethod
    def _serialized_public(public_signals):
        return [str(int(value)) for value in public_signals]

    @staticmethod
    def _decode_model_payload(payload, submission, expected_shapes):
        try:
            decoded = json.loads(payload.decode("utf-8"))
            if decoded["format"] != "fairai.parameters.v1":
                raise ValueError("unexpected parameter format")
            if decoded["round_id"] != submission["round_id"]:
                raise ValueError("round binding mismatch")
            if decoded["node_id"] != submission["node_id"]:
                raise ValueError("node binding mismatch")
            parameters = tuple(
                np.asarray(value, dtype=float) for value in decoded["parameters"]
            )
        except (KeyError, TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
            raise B2InfrastructureError(
                f"Approved model CID {submission['cids']['model']} is malformed: {exc}"
            ) from exc
        shapes = tuple(value.shape for value in parameters)
        if shapes != expected_shapes:
            raise B2InfrastructureError(
                f"Approved model CID {submission['cids']['model']} has unexpected parameter shapes"
            )
        if not all(np.isfinite(value).all() for value in parameters):
            raise B2InfrastructureError(
                f"Approved model CID {submission['cids']['model']} contains non-finite parameters"
            )
        return parameters

    def _cancel_round(self, round_id, reason):
        command = {"action": "cancel_round", "round_id": round_id, "reason": reason}
        self.protocol_commands.append(command)
        return self.bridge.request(command)

    def _retrieve_approved_models(
        self,
        round_id,
        eligible_cids,
        submissions_by_cid,
        model_payloads,
        update_shapes,
    ):
        from .ipfs import verify_payload

        retrieved_parameters = {}
        for cid in eligible_cids:
            submission = submissions_by_cid[cid]
            started = time.perf_counter()
            observed = self.consumer.cat(cid)
            retrieval_ms = (time.perf_counter() - started) * 1000
            expected = model_payloads[cid]
            verify_payload(expected, observed, cid)
            parameters = self._decode_model_payload(
                observed,
                submission,
                update_shapes[submission["client_id"]],
            )
            retrieved_parameters[submission["client_id"]] = parameters
            self.retrieval_rows.append(
                {
                    "round": round_id,
                    "client_id": submission["client_id"],
                    "artifact_type": "approved_model_master_retrieval",
                    "cid": cid,
                    "payload_bytes": len(observed),
                    "upload_ms": 0,
                    "retrieval_ms": retrieval_ms,
                    "verified": True,
                }
            )
        return retrieved_parameters

    def _retrieve_approved_models_or_cancel(self, **kwargs):
        try:
            return self._retrieve_approved_models(**kwargs)
        except Exception as exc:
            round_id = kwargs["round_id"]
            cancellation = self._cancel_round(
                round_id, "APPROVED_ARTIFACT_UNAVAILABLE"
            )
            raise ApprovedArtifactUnavailable(
                f"Approved model retrieval failed before aggregation: {exc}",
                cancellation,
            ) from exc

    def _inject_approved_artifact_failure(
        self, round_id, eligible_cids, submissions_by_cid
    ):
        fault = self.fault_injection or {}
        if fault.get("type") != "approved_artifact_unavailable":
            return
        if int(fault.get("round", 1)) != round_id:
            return
        configured_client = fault.get("client_id")
        if configured_client is None:
            target = eligible_cids[0] if eligible_cids else None
            target_client = (
                None if target is None else submissions_by_cid[target]["client_id"]
            )
        else:
            target_client = int(configured_client)
            target = next(
                (
                    cid
                    for cid in eligible_cids
                    if submissions_by_cid[cid]["client_id"] == target_client
                ),
                None,
            )
        if target is None:
            raise B2InfrastructureError(
                f"Fault target client {target_client} has no approved model in round {round_id}"
            )
        self.publisher.unpin(target, recursive=True)
        self.consumer.unpin(target, recursive=False)
        self.publisher.gc()
        self.consumer.gc()
        self.fault_injection_rows.append(
            {
                "type": fault["type"],
                "round_id": round_id,
                "client_id": target_client,
                "cid": target,
                "publisher_unpinned": True,
                "consumer_unpinned": True,
                "garbage_collection_completed": True,
            }
        )

    def _reported_metrics(self, round_id, client_metrics, policy):
        reported = {
            client_id: dict(metrics) for client_id, metrics in client_metrics.items()
        }
        experiment = self.metric_integrity_experiment or {}
        if experiment.get("type") != "false_metric_reporting":
            return reported
        if int(experiment.get("round", 1)) != round_id:
            return reported
        configured_client = experiment.get("client_id")
        if configured_client is None:
            target = next(
                (
                    client_id
                    for client_id in sorted(reported, key=int)
                    if not evaluate_policy(reported[client_id], policy, round_id)[
                        "approved"
                    ]
                ),
                None,
            )
        else:
            target = str(configured_client)
        if target not in reported:
            raise B2InfrastructureError(
                "False-metric experiment requires a target with genuine metrics"
            )
        genuine = client_metrics[target]
        genuine_decision = evaluate_policy(genuine, policy, round_id)
        fabricated = dict(genuine)
        fabricated.update(experiment["fabricated_metrics"])
        fabricated_decision = evaluate_policy(fabricated, policy, round_id)
        if genuine_decision["approved"]:
            raise B2InfrastructureError(
                "False-metric target must fail the policy using genuine metrics"
            )
        if not fabricated_decision["approved"]:
            raise B2InfrastructureError(
                "Fabricated metrics must pass the configured policy"
            )
        reported[target] = fabricated
        self.metric_integrity_rows.append(
            {
                "round_id": round_id,
                "client_id": target,
                "genuine_metrics": {
                    name: genuine.get(name)
                    for name in (
                        "accuracy",
                        "demographic_parity_gap",
                        "equal_opportunity_gap",
                        "equalized_odds_gap",
                        "subgroup_accuracy_gap",
                    )
                },
                "fabricated_metrics": {
                    name: fabricated.get(name)
                    for name in (
                        "accuracy",
                        "demographic_parity_gap",
                        "equal_opportunity_gap",
                        "equalized_odds_gap",
                        "subgroup_accuracy_gap",
                    )
                },
                "genuine_policy_approved": False,
                "reported_policy_approved": True,
                "proof_generated_over": "fabricated_metrics",
                "on_chain_approved": None,
                "aggregated": None,
            }
        )
        return reported

    def _write_evidence(self):
        startup = self.bridge.startup
        result = {
            "verifier_mode": "v2_groth16_eip712",
            "network": startup["network"],
            "chain_id": startup["chain_id"],
            "contract_address": startup["contract_address"],
            "groth16_verifier_address": startup["groth16_verifier_address"],
            "signed_verifier_address": startup["signed_verifier_address"],
            "composite_verifier_address": startup["composite_verifier_address"],
            "rounds": self.rounds,
            "kubo_version": self.kubo_version,
            "publisher_peer_id": self.publisher_id,
            "consumer_peer_id": self.consumer_id,
            "retrieval_rows": self.retrieval_rows,
            "proof_rows": self.proof_rows,
            "fault_injections": self.fault_injection_rows,
            "metric_integrity_experiment": self.metric_integrity_rows,
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "contract_input.json").write_text(
            json.dumps(
                {
                    "schema_version": "fairai.v2_round_protocol.v2",
                    "verifier_mode": "v2_groth16_eip712",
                    "commands": self.protocol_commands,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        (self.output_dir / "contract_result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
        )
        (self.output_dir / "v2_evidence.json").write_text(
            json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
        )
        return result

    def prepare_round(self, round_id, updates, client_metrics, policy):
        scale = 1_000_000
        reported_metrics = self._reported_metrics(
            round_id, client_metrics, policy
        )
        submissions = []
        model_payloads = {}
        update_shapes = {}
        for update in updates:
            if not update.valid or update.client_id not in client_metrics:
                continue
            client_id = update.client_id
            numeric_node_id = int(client_id) + 1
            nonce = round_id * 1_000_000 + numeric_node_id
            prefix = {"round_id": round_id, "node_id": numeric_node_id}
            scaled = self._scaled_metrics(reported_metrics[client_id], scale)
            metrics_artifact = {**prefix, **scaled}
            model_payload = _canonical_bytes(
                {**prefix, **_parameters_payload(update.parameters)}
            )
            model_cid = self._publish(
                round_id, client_id, "model", model_payload
            )
            model_payloads[model_cid] = model_payload
            update_shapes[client_id] = tuple(
                np.asarray(value).shape for value in update.parameters
            )
            cids = {
                "model": model_cid,
                "metrics": self._publish(
                    round_id,
                    client_id,
                    "metrics",
                    _canonical_bytes(metrics_artifact),
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
            binding = artifact_binding_fields(bound_manifest, metrics_artifact)
            circuit_input = self._circuit_input(
                scaled,
                policy,
                numeric_node_id,
                round_id,
                nonce,
                binding,
                scale,
            )
            decision = evaluate_policy(reported_metrics[client_id], policy, round_id)
            if decision["approved"]:
                proof_result = self.proof_system.prove(
                    circuit_input,
                    self.output_dir / "proofs" / f"round_{round_id}" / f"client_{client_id}",
                )
                if proof_result["public_signals"] != self._expected_public(circuit_input):
                    raise B2InfrastructureError("V2 public signals do not match bound inputs")
                proof_payload = proof_result["proof"]
                contract_proof = groth16_contract_proof(proof_payload)
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
            serialized_public = self._serialized_public(public_signals)
            cids["proof"] = self._publish(
                round_id,
                client_id,
                "proof",
                _canonical_bytes({**prefix, "proof": proof_payload}),
            )
            cids["public"] = self._publish(
                round_id,
                client_id,
                "public",
                _canonical_bytes({"public_signals": serialized_public}),
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
                    "public_signals": serialized_public,
                    "cids": cids,
                }
            )
        command = {
            "action": "submit_round",
            "round_id": round_id,
            "submissions": submissions,
        }
        self.protocol_commands.append(command)
        try:
            on_chain = self.bridge.request(command)
        except LedgerBridgeError as exc:
            self.bridge.close(force=True)
            raise B2InfrastructureError(f"On-chain round submission failed: {exc}") from exc
        expected_cids = sorted(
            item["cids"]["model"] for item in submissions if item["approved"]
        )
        eligible_cids = sorted(on_chain["eligible_model_cids"])
        records_by_node = {
            int(record["node_id"]): record for record in on_chain["records"]
        }
        for row in self.metric_integrity_rows:
            if row["round_id"] != round_id:
                continue
            node_id = int(row["client_id"]) + 1
            record = records_by_node[node_id]
            row["on_chain_approved"] = record["approval_status"] == "Approved"
            row["model_cid"] = record["model_cid"]
            row["submission_tx_hash"] = record["tx_hash"]
        if eligible_cids != expected_cids:
            cancellation = self._cancel_round(round_id, "ELIGIBILITY_MISMATCH")
            self.rounds.append({**on_chain, **cancellation})
            self._write_evidence()
            self.bridge.close(force=True)
            raise B2InfrastructureError(
                "On-chain eligible CIDs diverged from verified proof decisions"
            )

        submissions_by_cid = {item["cids"]["model"]: item for item in submissions}
        self._inject_approved_artifact_failure(
            round_id, eligible_cids, submissions_by_cid
        )
        try:
            retrieved_parameters = self._retrieve_approved_models_or_cancel(
                round_id=round_id,
                eligible_cids=eligible_cids,
                submissions_by_cid=submissions_by_cid,
                model_payloads=model_payloads,
                update_shapes=update_shapes,
            )
        except ApprovedArtifactUnavailable as exc:
            self.rounds.append({**on_chain, **exc.cancellation})
            self._write_evidence()
            self.bridge.close(force=True)
            raise

        approved_clients = [
            submissions_by_cid[cid]["client_id"] for cid in eligible_cids
        ]
        self.pending[round_id] = {
            "submissions": submissions,
            "on_chain": on_chain,
            "eligible_model_cids": eligible_cids,
            "retrieved_parameters": retrieved_parameters,
        }
        return {
            "approved_clients": approved_clients,
            "retrieved_parameters": retrieved_parameters,
            "eligible_model_cids": eligible_cids,
        }

    def record_round(
        self,
        round_id,
        updates,
        client_metrics,
        global_parameters,
        global_metrics,
        included_clients,
    ):
        pending = self.pending[round_id]
        submissions = pending["submissions"]
        approved_submissions = [
            item for item in submissions if item["client_id"] in set(included_clients)
        ]
        participant_cids = sorted(
            item["cids"]["model"] for item in approved_submissions
        )
        for row in self.metric_integrity_rows:
            if row["round_id"] == round_id:
                row["aggregated"] = row["client_id"] in set(included_clients)
        if participant_cids != pending["eligible_model_cids"]:
            cancellation = self._cancel_round(round_id, "AGGREGATION_SET_MISMATCH")
            self.rounds.append({**pending["on_chain"], **cancellation})
            self._write_evidence()
            self.bridge.close(force=True)
            raise B2InfrastructureError(
                "Aggregated clients do not match on-chain eligible model CIDs"
            )
        if not participant_cids:
            cancellation = self._cancel_round(round_id, "NO_ELIGIBLE_MODELS")
            self.rounds.append({**pending["on_chain"], **cancellation})
            self._write_evidence()
            return
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
        command = {
            "action": "publish_round",
            "round_id": round_id,
            "global_model_cid": global_model_cid,
            "report_cid": report_cid,
            "participant_model_cids": participant_cids,
        }
        self.protocol_commands.append(command)
        publication = self.bridge.request(command)
        self.rounds.append(
            {
                **pending["on_chain"],
                **publication,
                "global_publication": {
                    "global_model_cid": global_model_cid,
                    "report_cid": report_cid,
                    "participant_model_cids": participant_cids,
                },
            }
        )
        self._write_evidence()

    def finalize(self):
        if not self.rounds:
            raise B2InfrastructureError("No B4/B7 rounds were recorded")
        result = self._write_evidence()
        self.protocol_commands.append({"action": "close"})
        self.bridge.close()
        return result
