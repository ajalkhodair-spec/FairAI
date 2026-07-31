import argparse
from pathlib import Path

import pandas as pd


def describe(values, stage, evidence_type, source, status="measured"):
    values = pd.Series(values, dtype=float).dropna()
    if values.empty:
        return {
            "stage": stage,
            "status": status,
            "evidence_type": evidence_type,
            "n": 0,
            "mean_ms": None,
            "std_ms": None,
            "median_ms": None,
            "p95_ms": None,
            "minimum_ms": None,
            "maximum_ms": None,
            "source": source,
        }
    return {
        "stage": stage,
        "status": status,
        "evidence_type": evidence_type,
        "n": len(values),
        "mean_ms": values.mean(),
        "std_ms": values.std(ddof=1) if len(values) > 1 else 0.0,
        "median_ms": values.median(),
        "p95_ms": values.quantile(0.95),
        "minimum_ms": values.min(),
        "maximum_ms": values.max(),
        "source": source,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--federated-run", action="append", required=True)
    parser.add_argument("--legacy-run", required=True)
    args = parser.parse_args()
    rows = []
    for directory_value in args.federated_run:
        directory = Path(directory_value)
        client = pd.read_csv(
            directory / "metrics" / "fairness_metrics_by_client.csv"
        )
        test = pd.read_csv(directory / "metrics" / "test_metrics.csv")
        rows.append(
            describe(
                client["runtime_ms"],
                "local_train_evaluate_fairness_policy",
                "measured",
                str(
                    directory
                    / "metrics"
                    / "fairness_metrics_by_client.csv"
                ),
            )
        )
        rows.append(
            describe(
                test["runtime_ms"],
                "federated_method_total",
                "measured",
                str(directory / "metrics" / "test_metrics.csv"),
            )
        )
    legacy = Path(args.legacy_run)
    proof = pd.read_csv(legacy / "proof_timings.csv")
    rows.append(
        describe(
            proof["proof_generation_ms"],
            "legacy_proof_generation",
            "measured_legacy",
            str(legacy / "proof_timings.csv"),
        )
    )
    ipfs = pd.read_csv(legacy / "ipfs_timings.csv")
    rows.append(
        describe(
            ipfs["retrieval_ms"],
            "legacy_single_peer_ipfs_retrieval",
            "measured_legacy",
            str(legacy / "ipfs_timings.csv"),
        )
    )
    for stage, source in (
        ("v2_proof_generation", "BLOCKERS.md#BLK-001"),
        ("v2_proof_verification", "BLOCKERS.md#BLK-001"),
        ("two_peer_ipfs_add", "BLOCKERS.md#BLK-002"),
        ("two_peer_ipfs_pin", "BLOCKERS.md#BLK-002"),
        ("two_peer_ipfs_cold_retrieval", "BLOCKERS.md#BLK-002"),
        ("two_peer_ipfs_warm_retrieval", "BLOCKERS.md#BLK-002"),
        ("two_peer_ipfs_recovery", "BLOCKERS.md#BLK-002"),
    ):
        rows.append(describe([], stage, "missing", source, status="blocked"))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)


if __name__ == "__main__":
    main()
