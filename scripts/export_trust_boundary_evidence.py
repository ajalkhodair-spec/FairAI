import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_run(path):
    path = Path(path)
    manifest_path = path / "manifests" / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["completion_status"] != "completed" or manifest["dirty_tree"]:
        raise ValueError(f"Run must be clean and completed: {path}")
    contract_path = next(path.rglob("contract_result.json"))
    return manifest, contract_path, json.loads(contract_path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--false-metric-run", required=True)
    parser.add_argument("--unavailable-run", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    false_manifest, false_path, false = load_run(args.false_metric_run)
    unavailable_manifest, unavailable_path, unavailable = load_run(args.unavailable_run)
    metric_rows = false["metric_integrity_experiment"]
    if len(metric_rows) != 1:
        raise ValueError("Expected exactly one false-metric target")
    false_round = false["rounds"][0]
    false_row = metric_rows[0]
    if not (
        false_row["genuine_policy_approved"] is False
        and false_row["reported_policy_approved"] is True
        and false_row["on_chain_approved"] is True
        and false_row["aggregated"] is True
        and false_round["final_state"] == "Archived"
    ):
        raise ValueError("False-metric run did not demonstrate the expected trust boundary")
    unavailable_round = unavailable["rounds"][0]
    if not (
        unavailable_round["final_state"] == "Cancelled"
        and unavailable_round["reason"] == "APPROVED_ARTIFACT_UNAVAILABLE"
        and "global_publication" not in unavailable_round
    ):
        raise ValueError("Unavailable-artifact run did not fail closed")
    payload = {
        "schema_version": "fairai.trust_boundary_evidence.v1",
        "evidence_type": "derived_from_measured_full_path_runs",
        "false_metric_reporting": {
            **false_row,
            "round_final_state": false_round["final_state"],
            "eligible_model_cids": false_round["eligible_model_cids"],
            "approved_model_retrieval_verified": any(
                row["artifact_type"] == "approved_model_master_retrieval"
                and row["cid"] == false_row["model_cid"]
                and row["verified"]
                for row in false["retrieval_rows"]
            ),
        },
        "approved_artifact_unavailable": {
            "round_id": unavailable_round["round_id"],
            "eligible_model_cids": unavailable_round["eligible_model_cids"],
            "final_state": unavailable_round["final_state"],
            "reason": unavailable_round["reason"],
            "reason_code": unavailable_round["reason_code"],
            "cancellation_tx_hash": unavailable_round["cancellation_tx_hash"],
            "aggregation_started": False,
            "global_model_published": False,
            "fault_injections": unavailable["fault_injections"],
        },
        "inputs": {
            "false_metric_run": false_manifest["run_id"],
            "false_metric_commit": false_manifest["git_commit"],
            "false_metric_contract_sha256": sha256_file(false_path),
            "unavailable_run": unavailable_manifest["run_id"],
            "unavailable_commit": unavailable_manifest["git_commit"],
            "unavailable_contract_sha256": sha256_file(unavailable_path),
        },
        "claim_boundary": (
            "The proof establishes compliance and binding for supplied metrics; "
            "it does not establish correct derivation from private data."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
