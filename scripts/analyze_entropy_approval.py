import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
from scipy import stats


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_entropy(run_dir):
    rows = []
    pattern = "partitions/seed_*/clients_*/*/entropy_by_client.csv"
    for path in sorted(Path(run_dir).glob(pattern)):
        frame = pd.read_csv(path)
        frame["seed"] = int(path.parts[-4].removeprefix("seed_"))
        frame["client_count"] = int(path.parts[-3].removeprefix("clients_"))
        frame["partition"] = path.parts[-2]
        frame["minority_fraction"] = frame["group_distribution"].map(
            lambda value: min(json.loads(value).values())
            / sum(json.loads(value).values())
        )
        rows.append(frame)
    if not rows:
        raise ValueError("No entropy_by_client.csv files found")
    return pd.concat(rows, ignore_index=True)


def analyze(run_dir, output_dir, method):
    run_dir = Path(run_dir)
    metrics_path = run_dir / "metrics" / "fairness_metrics_by_client.csv"
    metrics = pd.read_csv(metrics_path)
    selected = metrics[metrics["method"] == method].copy()
    selected = selected[selected["round"] == selected["round"].max()]
    entropy = load_entropy(run_dir)
    joined = selected.merge(
        entropy,
        on=["seed", "client_count", "partition", "client_id"],
        validate="one_to_one",
    )
    joined["approved_numeric"] = joined["approved"].astype(int)
    joined["excluded_numeric"] = 1 - joined["approved_numeric"]
    groups = ["seed", "client_count", "partition"]
    totals = joined.groupby(groups)["sample_count"].transform("sum")
    joined["excluded_sample_fraction"] = (
        joined["sample_count"] / totals * joined["excluded_numeric"]
    )
    medians = joined.groupby(groups)["minority_fraction"].transform("median")
    joined["minority_heavy"] = joined["minority_fraction"] >= medians
    correlations = []
    outcomes = (
        "approved_numeric", "excluded_numeric", "excluded_sample_fraction",
        "minority_fraction", "demographic_parity_gap", "equal_opportunity_gap",
        "equalized_odds_gap", "subgroup_accuracy_gap",
    )
    for partition, group in joined.groupby("partition", sort=True):
        for entropy_name in ("label_entropy", "group_entropy"):
            for outcome in outcomes:
                values = group[[entropy_name, outcome]].dropna()
                result = stats.spearmanr(values[entropy_name], values[outcome])
                correlations.append(
                    {
                        "partition": partition, "entropy_metric": entropy_name,
                        "outcome": outcome, "n": len(values),
                        "spearman_rho": result.statistic, "p_value": result.pvalue,
                    }
                )
    representation = (
        joined.groupby(["partition", "minority_heavy"], sort=True)
        .agg(
            clients=("client_id", "size"),
            approval_rate=("approved_numeric", "mean"),
            rejection_rate=("excluded_numeric", "mean"),
            mean_minority_fraction=("minority_fraction", "mean"),
            excluded_sample_fraction=("excluded_sample_fraction", "sum"),
        )
        .reset_index()
    )
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    joined.to_csv(output_dir / "entropy_approval_joined.csv", index=False)
    pd.DataFrame(correlations).to_csv(output_dir / "entropy_correlations.csv", index=False)
    representation.to_csv(output_dir / "representation_fairness.csv", index=False)
    manifest = {
        "schema_version": "fairai.entropy_approval_analysis.v1",
        "evidence_type": "derived", "method": method, "final_round_only": True,
        "inputs": {
            "run_id": json.loads((run_dir / "manifests/run_manifest.json").read_text())["run_id"],
            "metrics_sha256": sha256_file(metrics_path),
        },
        "outputs": {path.name: sha256_file(path) for path in sorted(output_dir.glob("*.csv"))},
    }
    (output_dir / "analysis_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--method", default="B3")
    args = parser.parse_args()
    print(json.dumps(analyze(args.run, args.output, args.method), indent=2))


if __name__ == "__main__":
    main()
