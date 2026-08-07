import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np

from .ipfs import KuboClient, connect_two_peers, verify_payload


class B2InfrastructureError(RuntimeError):
    pass


def _canonical_bytes(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _parameters_payload(parameters):
    return {
        "format": "fairai.parameters.v1",
        "parameters": [np.asarray(value, dtype=float).tolist() for value in parameters],
    }


class B2KuboLedgerAdapter:
    """Strict B2 adapter: real Kubo retrieval plus one multi-round ledger."""

    def __init__(
        self,
        output_dir,
        repo_root,
        publisher_api="http://127.0.0.1:5001",
        consumer_api="http://127.0.0.1:5002",
        kubo_version="0.29.0",
        publisher_swarm_host="ipfs-publisher",
        ipfs_timeout_seconds=60,
    ):
        self.output_dir = Path(output_dir)
        self.repo_root = Path(repo_root)
        self.publisher = KuboClient(publisher_api, timeout_seconds=ipfs_timeout_seconds)
        self.consumer = KuboClient(consumer_api, timeout_seconds=ipfs_timeout_seconds)
        versions = (self.publisher.version()["Version"], self.consumer.version()["Version"])
        if versions != (kubo_version, kubo_version):
            raise B2InfrastructureError(
                f"Kubo version mismatch: publisher={versions[0]}, consumer={versions[1]}, expected={kubo_version}"
            )
        self.publisher_id, self.consumer_id = connect_two_peers(
            self.publisher, self.consumer, publisher_swarm_host
        )
        self.kubo_version = kubo_version
        self.rounds = []
        self.retrieval_rows = []

    def _publish(self, round_id, client_id, artifact_type, payload):
        started = time.perf_counter()
        cid = self.publisher.add(payload, filename=f"{artifact_type}.json")
        upload_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        observed = self.consumer.cat(cid)
        retrieval_ms = (time.perf_counter() - started) * 1000
        verify_payload(payload, observed, cid)
        started = time.perf_counter()
        self.consumer.pin(cid)
        pin_ms = (time.perf_counter() - started) * 1000
        self.retrieval_rows.append(
            {
                "round": round_id,
                "client_id": client_id,
                "artifact_type": artifact_type,
                "cid": cid,
                "payload_bytes": len(payload),
                "upload_ms": upload_ms,
                "retrieval_ms": retrieval_ms,
                "pin_ms": pin_ms,
                "verified": True,
            }
        )
        return cid

    def record_round(
        self,
        round_id,
        updates,
        client_metrics,
        global_parameters,
        global_metrics,
        included_clients,
    ):
        included = set(included_clients)
        submissions = []
        for update in updates:
            if update.client_id not in included:
                continue
            prefix = {"round_id": round_id, "node_id": update.client_id}
            artifacts = {
                "model": self._publish(
                    round_id,
                    update.client_id,
                    "model",
                    _canonical_bytes({**prefix, **_parameters_payload(update.parameters)}),
                ),
                "metrics": self._publish(
                    round_id,
                    update.client_id,
                    "metrics",
                    _canonical_bytes({**prefix, "metrics": client_metrics[update.client_id]}),
                ),
                "metadata": self._publish(
                    round_id,
                    update.client_id,
                    "metadata",
                    _canonical_bytes(
                        {
                            **prefix,
                            "method": "B2",
                            "sample_count": update.sample_count,
                            "proof_mode": "not_applicable_infrastructure_baseline",
                        }
                    ),
                ),
            }
            for name in ("proof", "public"):
                artifacts[name] = self._publish(
                    round_id,
                    update.client_id,
                    name,
                    _canonical_bytes(
                        {
                            **prefix,
                            "artifact": name,
                            "status": "not_applicable_infrastructure_baseline",
                        }
                    ),
                )
            manifest = {
                "schema_version": "fairai.b2_manifest.v1",
                **prefix,
                "method": "B2",
                "artifacts": artifacts,
            }
            artifacts["manifest"] = self._publish(
                round_id,
                update.client_id,
                "manifest",
                _canonical_bytes(manifest),
            )
            submissions.append(
                {"node_id": update.client_id, "round_id": round_id, "cids": artifacts}
            )

        global_model_cid = self._publish(
            round_id,
            "global",
            "global_model",
            _canonical_bytes(
                {
                    "round_id": round_id,
                    "method": "B2",
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
                    "schema_version": "fairai.b2_round_report.v1",
                    "round_id": round_id,
                    "global_metrics": global_metrics,
                    "participant_nodes": sorted(included),
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
                    "participant_model_cids": [item["cids"]["model"] for item in submissions],
                },
            }
        )

    def finalize(self):
        if not self.rounds:
            raise B2InfrastructureError("No B2 rounds were recorded")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        input_path = self.output_dir / "contract_input.json"
        output_path = self.output_dir / "contract_result.json"
        input_path.write_text(
            json.dumps(
                {
                    "schema_version": "fairai.b2_contract_input.v1",
                    "verifier_mode": "infrastructure_passthrough",
                    "rounds": self.rounds,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        env = {
            **os.environ,
            "FAIRAI_CONTRACT_INPUT": str(input_path.resolve()),
            "FAIRAI_CONTRACT_OUTPUT": str(output_path.resolve()),
        }
        completed = subprocess.run(
            ["npx", "hardhat", "run", "scripts/run_infrastructure_rounds.js"],
            cwd=self.repo_root / "hardhat",
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if completed.returncode != 0:
            raise B2InfrastructureError(
                "B2 ledger execution failed:\n" + completed.stdout
            )
        result = json.loads(output_path.read_text(encoding="utf-8"))
        if len(result["rounds"]) != len(self.rounds):
            raise B2InfrastructureError("Ledger round count does not match recorded rounds")
        for expected, observed in zip(self.rounds, result["rounds"]):
            expected_cids = sorted(
                item["cids"]["model"] for item in expected["submissions"]
            )
            if observed["final_state"] != "Archived":
                raise B2InfrastructureError("B2 ledger round did not reach Archived")
            if sorted(observed["eligible_model_cids"]) != expected_cids:
                raise B2InfrastructureError("B2 ledger eligible CIDs do not match IPFS artifacts")
        result.update(
            {
                "kubo_version": self.kubo_version,
                "publisher_peer_id": self.publisher_id,
                "consumer_peer_id": self.consumer_id,
                "retrieval_rows": self.retrieval_rows,
            }
        )
        (self.output_dir / "b2_evidence.json").write_text(
            json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
        )
        return result
