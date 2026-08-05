import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analyze_expanded_results import load_completed, sha256_file, summarize


def load_clean_manifest(directory):
    path = directory / "manifests" / "run_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["completion_status"] != "completed" or manifest["dirty_tree"]:
        raise ValueError(f"Input is not a clean completed run: {directory}")
    return manifest, path


def percentile95(values):
    return float(np.percentile(np.asarray(values, dtype=float), 95))


def analyze_ipfs(directory):
    manifest, manifest_path = load_clean_manifest(directory)
    raw_path = directory / "raw" / "ipfs_benchmark.csv"
    frame = pd.read_csv(raw_path)
    if len(frame) != 270 or not frame["verified"].all():
        raise ValueError("Strict IPFS benchmark is incomplete or unverified")

    sequential_rows = []
    sequential = frame[frame["mode"] == "sequential"]
    for size, group in sequential.groupby("payload_bytes", sort=True):
        row = {"payload_bytes": int(size), "n": len(group)}
        for metric in (
            "upload_ms",
            "cold_retrieval_ms",
            "warm_retrieval_ms",
            "pin_ms",
        ):
            values = group[metric].to_numpy(dtype=float)
            row.update(
                {
                    f"{metric}_mean": float(values.mean()),
                    f"{metric}_median": float(np.median(values)),
                    f"{metric}_p95": percentile95(values),
                }
            )
        sequential_rows.append(row)

    concurrency_rows = []
    concurrent = frame[frame["mode"] == "concurrent"].copy()
    concurrent["throughput_mib_s"] = (
        concurrent["concurrency"] * concurrent["payload_bytes"] / 1048576
    ) / (concurrent["cold_retrieval_ms"] / 1000)
    for concurrency, group in concurrent.groupby("concurrency", sort=True):
        elapsed = group["cold_retrieval_ms"].to_numpy(dtype=float)
        throughput = group["throughput_mib_s"].to_numpy(dtype=float)
        concurrency_rows.append(
            {
                "concurrency": int(concurrency),
                "payload_bytes_each": int(group["payload_bytes"].iloc[0]),
                "n": len(group),
                "elapsed_ms_mean": float(elapsed.mean()),
                "elapsed_ms_median": float(np.median(elapsed)),
                "elapsed_ms_p95": percentile95(elapsed),
                "throughput_mib_s_mean": float(throughput.mean()),
                "throughput_mib_s_p95": percentile95(throughput),
            }
        )
    return sequential_rows, concurrency_rows, {
        "run_id": manifest["run_id"],
        "git_commit": manifest["git_commit"],
        "configuration_hash": manifest["configuration_hash"],
        "kubo_version": manifest["environment"]["kubo_version"],
        "raw_sha256": sha256_file(raw_path),
        "manifest_sha256": sha256_file(manifest_path),
    }


def analyze_bounded(directory):
    metrics, input_evidence = load_completed(directory)
    descriptive = summarize(metrics, "kubo_v2_bounded", ["client_count", "method"])
    retrieval_rows = []
    proof_rows = []
    ledger_records = []
    publication_gas = []
    states = []
    evidence_files = []
    for evidence_path in sorted((directory / "infrastructure").glob("*/**evidence.json")):
        match = re.search(r"clients_(\d+).+-(B2|B4|B7)$", evidence_path.parent.name)
        if match is None:
            raise ValueError(f"Cannot classify infrastructure evidence: {evidence_path}")
        client_count, method = int(match.group(1)), match.group(2)
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence_files.append(
            {"path": str(evidence_path.relative_to(directory)), "sha256": sha256_file(evidence_path)}
        )
        for row in evidence["retrieval_rows"]:
            retrieval_rows.append({"client_count": client_count, "method": method, **row})
        for row in evidence.get("proof_rows", []):
            proof_rows.append({"client_count": client_count, "method": method, **row})
        for round_row in evidence["rounds"]:
            states.append(round_row["final_state"])
            for record in round_row["records"]:
                ledger_records.append(
                    {"client_count": client_count, "method": method, **record}
                )
            gas = round_row.get("publication_gas_used")
            if gas is None and round_row.get("publication"):
                gas = round_row["publication"].get("gas_used")
            if gas is not None:
                publication_gas.append(int(gas))

    if len(evidence_files) != 18:
        raise ValueError("Expected 18 strict infrastructure executions")
    if not retrieval_rows or not all(row["verified"] for row in retrieval_rows):
        raise ValueError("Infrastructure retrieval evidence is incomplete")
    record_gas = [int(row["gas_used"]) for row in ledger_records]
    summary = {
        "schema_version": "fairai.infrastructure_analysis.v1",
        "evidence_type": "derived",
        "executions": len(evidence_files),
        "retrieval_checks": len(retrieval_rows),
        "retrieval_verified": sum(bool(row["verified"]) for row in retrieval_rows),
        "retrieval_ms_mean": float(np.mean([row["retrieval_ms"] for row in retrieval_rows])),
        "retrieval_ms_p95": percentile95([row["retrieval_ms"] for row in retrieval_rows]),
        "proof_decisions": len(proof_rows),
        "proofs_generated": sum(bool(row["approved"]) for row in proof_rows),
        "policy_rejections_without_proof": sum(not bool(row["approved"]) for row in proof_rows),
        "ledger_records": len(ledger_records),
        "approved_records": sum(row["approval_status"] == "Approved" for row in ledger_records),
        "rejected_records": sum(row["approval_status"] == "Rejected" for row in ledger_records),
        "archived_rounds": states.count("Archived"),
        "cancelled_rounds": states.count("Cancelled"),
        "submission_gas_mean": float(np.mean(record_gas)),
        "submission_gas_p95": percentile95(record_gas),
        "publication_gas_mean": float(np.mean(publication_gas)),
        "publication_gas_p95": percentile95(publication_gas),
        "input": input_evidence,
        "evidence_files": evidence_files,
    }
    return descriptive, summary


def analyze_recovery(directory):
    manifest, manifest_path = load_clean_manifest(directory)
    raw_path = directory / "raw" / "ipfs_recovery.csv"
    summary_path = directory / "derived" / "summary.json"
    frame = pd.read_csv(raw_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        len(frame) != 30
        or not frame["verified"].all()
        or not frame["publisher_identity_stable"].all()
        or not summary["verified"]
        or not summary["publisher_identity_stable"]
    ):
        raise ValueError("Native Kubo recovery evidence is incomplete")
    row = {
        "payload_bytes": int(frame["payload_bytes"].iloc[0]),
        "n": len(frame),
    }
    for metric in (
        "pin_ms",
        "outage_retrieval_ms",
        "restart_ready_ms",
        "recovery_verified_ms",
    ):
        values = frame[metric].to_numpy(dtype=float)
        row.update(
            {
                f"{metric}_mean": float(values.mean()),
                f"{metric}_median": float(np.median(values)),
                f"{metric}_p95": percentile95(values),
            }
        )
    return row, {
        "run_id": manifest["run_id"],
        "git_commit": manifest["git_commit"],
        "configuration_hash": manifest["configuration_hash"],
        "kubo_version": manifest["environment"]["kubo_version"],
        "raw_sha256": sha256_file(raw_path),
        "summary_sha256": sha256_file(summary_path),
        "manifest_sha256": sha256_file(manifest_path),
    }


def analyze(args):
    ipfs_dir = Path(args.ipfs)
    bounded_dir = Path(args.bounded)
    recovery_dir = Path(args.recovery)
    sequential, concurrency, ipfs_input = analyze_ipfs(ipfs_dir)
    bounded, infrastructure = analyze_bounded(bounded_dir)
    recovery, recovery_input = analyze_recovery(recovery_dir)
    infrastructure["recovery"] = recovery
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    paths = {
        "ipfs_sequential.csv": pd.DataFrame(sequential),
        "ipfs_concurrency.csv": pd.DataFrame(concurrency),
        "bounded_metrics.csv": pd.DataFrame(bounded),
        "ipfs_recovery.csv": pd.DataFrame([recovery]),
    }
    hashes = {}
    for name, frame in paths.items():
        path = output / name
        frame.to_csv(path, index=False)
        hashes[name] = sha256_file(path)
    summary_path = output / "infrastructure_summary.json"
    summary_path.write_text(
        json.dumps(infrastructure, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    hashes[summary_path.name] = sha256_file(summary_path)
    manifest = {
        "schema_version": "fairai.infrastructure_analysis_manifest.v1",
        "evidence_type": "derived",
        "analysis_git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip(),
        "ipfs_input": ipfs_input,
        "bounded_input": infrastructure["input"],
        "recovery_input": recovery_input,
        "outputs": hashes,
    }
    (output / "analysis_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), **{k: infrastructure[k] for k in ("executions", "retrieval_checks", "proofs_generated", "ledger_records")}}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Analyze strict Kubo and V2 infrastructure runs")
    parser.add_argument("--ipfs", required=True)
    parser.add_argument("--bounded", required=True)
    parser.add_argument("--recovery", required=True)
    parser.add_argument("--output", required=True)
    analyze(parser.parse_args())


if __name__ == "__main__":
    main()
