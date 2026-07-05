#!/usr/bin/env python3
import argparse
import csv
import json
import statistics
import time
from pathlib import Path

from fairai_mvp import run_pipeline


def mean(values):
    return round(statistics.mean(values), 6) if values else 0


def main():
    parser = argparse.ArgumentParser(description="Run repeated FairAI MVP trials and export aggregate metrics.")
    parser.add_argument("--output", default="runs/experiment", help="Experiment output directory.")
    parser.add_argument("--trials", type=int, default=3, help="Number of repeated trials.")
    parser.add_argument("--force-zk", action="store_true", help="Rebuild circuit artifacts before each run.")
    parser.add_argument("--require-real-ipfs", action="store_true", help="Fail if Kubo/IPFS is unavailable.")
    args = parser.parse_args()

    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    for trial in range(1, args.trials + 1):
        started = time.time()
        summary = run_pipeline(
            output_dir / f"trial_{trial}",
            force_zk=args.force_zk,
            require_real_ipfs=args.require_real_ipfs,
        )
        proof_times = summary["instrumentation"]["proof_generation_ms"]
        retrieval_times = [
            item["retrieval_ms"]
            for item in summary["instrumentation"]["ipfs_retrieval_checks"]
            if item.get("valid")
        ]
        rows.append({
            "trial": trial,
            "runtime_ms": round((time.time() - started) * 1000, 3),
            "approved_nodes": summary["approved_nodes"],
            "rejected_nodes": summary["rejected_nodes"],
            "approval_rate": round(summary["approved_nodes"] / summary["nodes_total"], 6),
            "global_accuracy": summary["global_model"]["validation_metrics"]["accuracy"],
            "global_demographic_parity_gap": summary["global_model"]["validation_metrics"]["demographic_parity_gap"],
            "mean_proof_generation_ms": mean(proof_times),
            "mean_ipfs_retrieval_ms": mean(retrieval_times),
            "global_publication_gas": summary["global_publication"]["gas_used"],
            "global_model_cid": summary["global_model_cid"],
            "report_cid": summary["report_cid"],
        })

    with (output_dir / "experiment_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    aggregate = {
        "trials": args.trials,
        "mean_approval_rate": mean([row["approval_rate"] for row in rows]),
        "mean_global_accuracy": mean([row["global_accuracy"] for row in rows]),
        "mean_global_demographic_parity_gap": mean([row["global_demographic_parity_gap"] for row in rows]),
        "mean_proof_generation_ms": mean([row["mean_proof_generation_ms"] for row in rows]),
        "mean_ipfs_retrieval_ms": mean([row["mean_ipfs_retrieval_ms"] for row in rows]),
        "rows": rows,
    }
    (output_dir / "experiment_summary.json").write_text(json.dumps(aggregate, indent=2, sort_keys=True))
    print(json.dumps(aggregate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
