import argparse
import csv
import hashlib
import json
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_bool(value):
    if value in (True, "True", "true", "1", 1):
        return True
    if value in (False, "False", "false", "0", 0):
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def mean(values):
    return float(statistics.fmean(values))


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"Cannot write empty evidence: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def analyze(args):
    source = Path(args.input)
    manifest_path = source / "manifests" / "run_manifest.json"
    summary_path = source / "derived" / "summary.json"
    test_path = source / "metrics" / "test_metrics.csv"
    client_path = source / "metrics" / "fairness_metrics_by_client.csv"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if manifest["completion_status"] != "completed" or manifest["dirty_tree"]:
        raise ValueError("Adversarial input must be a clean completed run")
    if manifest["scenario_id"] != "kubo_v2_adversarial":
        raise ValueError("Unexpected adversarial scenario")

    with test_path.open(encoding="utf-8", newline="") as handle:
        test_rows = list(csv.DictReader(handle))
    with client_path.open(encoding="utf-8", newline="") as handle:
        client_rows = list(csv.DictReader(handle))
    methods = run_summary["methods_executed"]
    attacks = run_summary["attack_profiles"]
    seeds = run_summary["experiment_seeds"]
    expected_executions = len(methods) * len(attacks) * len(seeds)
    if len(test_rows) != expected_executions:
        raise ValueError("Adversarial test matrix is incomplete")

    grouped_tests = defaultdict(list)
    for row in test_rows:
        grouped_tests[(row["method"], row["attack_type"])].append(row)
    summary_rows = []
    for method in methods:
        baseline = {
            int(row["seed"]): float(row["accuracy"])
            for row in grouped_tests[(method, "none")]
        }
        if set(baseline) != set(seeds):
            raise ValueError(f"Incomplete baseline for {method}")
        for attack in attacks:
            rows = grouped_tests[(method, attack)]
            observed_seeds = {int(row["seed"]) for row in rows}
            if observed_seeds != set(seeds):
                raise ValueError(f"Incomplete {method}/{attack} result")
            accuracy = [float(row["accuracy"]) for row in rows]
            eo_gap = [float(row["equalized_odds_gap"]) for row in rows]
            runtime = [float(row["runtime_ms"]) for row in rows]
            paired_delta = [
                float(row["accuracy"]) - baseline[int(row["seed"])]
                for row in rows
            ]
            summary_rows.append(
                {
                    "method": method,
                    "attack_type": attack,
                    "n": len(rows),
                    "accuracy_mean": mean(accuracy),
                    "accuracy_min": min(accuracy),
                    "accuracy_max": max(accuracy),
                    "accuracy_delta_vs_none_mean": mean(paired_delta),
                    "equalized_odds_gap_mean": mean(eo_gap),
                    "runtime_ms_mean": mean(runtime),
                }
            )

    grouped_clients = defaultdict(list)
    for row in client_rows:
        grouped_clients[(row["method"], row["attack_type"])].append(row)
    approval_rows = []
    for method in methods:
        for attack in attacks:
            rows = grouped_clients[(method, attack)]
            malicious = [row for row in rows if parse_bool(row["malicious_client"])]
            benign = [row for row in rows if not parse_bool(row["malicious_client"])]
            malicious_approved = sum(parse_bool(row["approved"]) for row in malicious)
            benign_approved = sum(parse_bool(row["approved"]) for row in benign)
            approval_rows.append(
                {
                    "method": method,
                    "attack_type": attack,
                    "malicious_submissions": len(malicious),
                    "malicious_approved": malicious_approved,
                    "malicious_approval_rate": (
                        malicious_approved / len(malicious) if malicious else ""
                    ),
                    "benign_submissions": len(benign),
                    "benign_approved": benign_approved,
                    "benign_approval_rate": benign_approved / len(benign),
                }
            )

    evidence_paths = sorted((source / "infrastructure").glob("*/v2_evidence.json"))
    contract_paths = sorted((source / "infrastructure").glob("*/contract_result.json"))
    if len(evidence_paths) != expected_executions or len(contract_paths) != expected_executions:
        raise ValueError("Adversarial infrastructure evidence is incomplete")
    retrievals = []
    proofs = []
    records = []
    states = []
    for path in evidence_paths:
        evidence = json.loads(path.read_text(encoding="utf-8"))
        retrievals.extend(evidence["retrieval_rows"])
        proofs.extend(evidence["proof_rows"])
    for path in contract_paths:
        result = json.loads(path.read_text(encoding="utf-8"))
        for round_row in result["rounds"]:
            states.append(round_row["final_state"])
            records.extend(round_row["records"])
    if not retrievals or not all(parse_bool(row["verified"]) for row in retrievals):
        raise ValueError("At least one IPFS retrieval is missing or unverified")

    infrastructure = {
        "schema_version": "fairai.adversarial_infrastructure.v1",
        "evidence_type": "derived",
        "executions": expected_executions,
        "rounds": len(states),
        "round_states": dict(sorted(Counter(states).items())),
        "proof_decisions": len(proofs),
        "proofs_generated": sum(float(row["proof_ms"]) > 0 for row in proofs),
        "ledger_records": len(records),
        "approved_records": sum(row["approval_status"] == "Approved" for row in records),
        "rejected_records": sum(row["approval_status"] == "Rejected" for row in records),
        "ipfs_retrieval_checks": len(retrievals),
        "ipfs_retrievals_verified": sum(parse_bool(row["verified"]) for row in retrievals),
    }

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    summary_output = output / "adversarial_summary.csv"
    approval_output = output / "adversarial_approval.csv"
    infrastructure_output = output / "adversarial_infrastructure.json"
    write_csv(summary_output, summary_rows)
    write_csv(approval_output, approval_rows)
    infrastructure_output.write_text(
        json.dumps(infrastructure, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    input_files = [manifest_path, summary_path, test_path, client_path, *evidence_paths, *contract_paths]
    analysis_manifest = {
        "schema_version": "fairai.adversarial_analysis_manifest.v1",
        "evidence_type": "derived",
        "analysis_git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip(),
        "input_run_id": manifest["run_id"],
        "input_git_commit": manifest["git_commit"],
        "input_configuration_hash": manifest["configuration_hash"],
        "input_files": {
            str(path.relative_to(source)): sha256_file(path) for path in input_files
        },
        "outputs": {
            path.name: sha256_file(path)
            for path in (summary_output, approval_output, infrastructure_output)
        },
    }
    (output / "analysis_manifest.json").write_text(
        json.dumps(analysis_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), **infrastructure}, indent=2, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description="Analyze strict adversarial Kubo V2 evidence")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    analyze(parser.parse_args())


if __name__ == "__main__":
    main()
