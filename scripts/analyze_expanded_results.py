import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


METRICS = [
    "accuracy",
    "macro_f1",
    "demographic_parity_gap",
    "equal_opportunity_gap",
    "equalized_odds_gap",
    "subgroup_accuracy_gap",
    "runtime_ms",
]


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize(frame, suite, dimensions):
    rows = []
    for keys, group in frame.groupby(dimensions, dropna=False, sort=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        labels = dict(zip(dimensions, keys))
        for metric in METRICS:
            values = group[metric].dropna().to_numpy(dtype=float)
            if not len(values):
                continue
            mean = values.mean()
            std = values.std(ddof=1) if len(values) > 1 else 0.0
            sem = std / math.sqrt(len(values)) if len(values) > 1 else 0.0
            critical = (
                stats.t.ppf(0.975, len(values) - 1)
                if len(values) > 1
                else 0.0
            )
            rows.append(
                {
                    "suite": suite,
                    **labels,
                    "metric": metric,
                    "n": len(values),
                    "mean": mean,
                    "std": std,
                    "ci95_low": mean - critical * sem,
                    "ci95_high": mean + critical * sem,
                    "minimum": values.min(),
                    "maximum": values.max(),
                }
            )
    return rows


def paired_rows(frame, suite, dimensions, left, right):
    rows = []
    for keys, group in frame.groupby(dimensions, dropna=False, sort=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        labels = dict(zip(dimensions, keys))
        for metric in METRICS[:-1]:
            pivot = group.pivot(index="seed", columns="method", values=metric)
            if left not in pivot or right not in pivot:
                continue
            paired = pivot[[left, right]].dropna()
            if len(paired) < 2:
                continue
            differences = paired[right] - paired[left]
            if np.allclose(differences, 0):
                t_statistic, t_p = 0.0, 1.0
                wilcoxon_statistic, wilcoxon_p = 0.0, 1.0
            else:
                t_result = stats.ttest_rel(paired[right], paired[left])
                t_statistic, t_p = t_result.statistic, t_result.pvalue
                wilcoxon_result = stats.wilcoxon(
                    paired[right], paired[left]
                )
                wilcoxon_statistic = wilcoxon_result.statistic
                wilcoxon_p = wilcoxon_result.pvalue
            difference_std = differences.std(ddof=1)
            effect = (
                None
                if np.isclose(difference_std, 0)
                else differences.mean() / difference_std
            )
            rows.append(
                {
                    "suite": suite,
                    **labels,
                    "comparison": f"{right}-{left}",
                    "metric": metric,
                    "n": len(paired),
                    "mean_difference": differences.mean(),
                    "paired_effect_size_dz": effect,
                    "paired_t_statistic": t_statistic,
                    "paired_t_p": t_p,
                    "wilcoxon_statistic": wilcoxon_statistic,
                    "wilcoxon_p": wilcoxon_p,
                }
            )
    return rows


def holm_adjust(rows):
    if not rows:
        return
    p_values = np.asarray([row["paired_t_p"] for row in rows], dtype=float)
    order = np.argsort(p_values)
    adjusted = np.empty(len(rows), dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        candidate = min(1.0, (len(rows) - rank) * p_values[index])
        running = max(running, candidate)
        adjusted[index] = running
    for row, value in zip(rows, adjusted):
        row["paired_t_p_holm"] = value


def entropy_correlations(heterogeneity_dir, metrics):
    entropy_rows = []
    for path in sorted(
        (heterogeneity_dir / "partitions").glob(
            "seed_*/clients_*/**/entropy_summary.csv"
        )
    ):
        seed = int(path.parts[-4].removeprefix("seed_"))
        partition = path.parent.name
        values = pd.read_csv(path).set_index("metric")["mean"]
        entropy_rows.append(
            {
                "seed": seed,
                "partition": partition,
                "mean_label_entropy": values["label_entropy"],
                "mean_group_entropy": values["group_entropy"],
            }
        )
    merged = metrics.merge(pd.DataFrame(entropy_rows), on=["seed", "partition"])
    rows = []
    for entropy_metric in ("mean_label_entropy", "mean_group_entropy"):
        for outcome in METRICS[:-1]:
            values = merged[[entropy_metric, outcome]].dropna()
            correlation = stats.spearmanr(
                values[entropy_metric], values[outcome]
            )
            rows.append(
                {
                    "entropy_metric": entropy_metric,
                    "outcome": outcome,
                    "n": len(values),
                    "spearman_rho": correlation.statistic,
                    "p_value": correlation.pvalue,
                }
            )
    return rows


def load_completed(directory):
    manifest_path = directory / "manifests" / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["completion_status"] != "completed" or manifest["dirty_tree"]:
        raise ValueError(f"Input is not a clean completed run: {directory}")
    metrics_path = directory / "metrics" / "test_metrics.csv"
    return pd.read_csv(metrics_path), {
        "run_id": manifest["run_id"],
        "git_commit": manifest["git_commit"],
        "configuration_hash": manifest["configuration_hash"],
        "metrics_sha256": sha256_file(metrics_path),
    }


def analyze(args):
    directories = {
        "mlp": Path(args.mlp),
        "scaling": Path(args.scaling),
        "heterogeneity": Path(args.heterogeneity),
        "threshold": Path(args.threshold),
        "adversarial": Path(args.adversarial),
    }
    frames = {}
    inputs = {}
    for name, directory in directories.items():
        frames[name], inputs[name] = load_completed(directory)

    summary_rows = []
    summary_rows += summarize(frames["mlp"], "mlp", ["method"])
    summary_rows += summarize(
        frames["scaling"], "scaling", ["client_count", "method"]
    )
    summary_rows += summarize(
        frames["heterogeneity"], "heterogeneity", ["partition", "method"]
    )
    summary_rows += summarize(
        frames["threshold"], "threshold", ["policy_profile", "method"]
    )
    summary_rows += summarize(
        frames["adversarial"],
        "adversarial",
        ["attack_type", "method"],
    )

    paired = paired_rows(frames["mlp"], "mlp", ["partition"], "B0", "B1")
    paired += paired_rows(
        frames["adversarial"],
        "adversarial",
        ["attack_type"],
        "B0",
        "B6",
    )
    holm_adjust(paired)

    global_threshold = pd.read_csv(
        directories["threshold"] / "metrics" / "fairness_metrics_global.csv"
    )
    final_round = global_threshold[
        global_threshold["round"] == global_threshold["round"].max()
    ]
    approval = (
        final_round.groupby("policy_profile", sort=True)["approval_rate"]
        .agg(["count", "mean", "std", "min", "max"])
        .reset_index()
    )

    entropy = entropy_correlations(
        directories["heterogeneity"], frames["heterogeneity"]
    )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    pd.DataFrame(summary_rows).to_csv(
        output / "experiment_summary.csv", index=False
    )
    pd.DataFrame(paired).to_csv(
        output / "paired_comparisons.csv", index=False
    )
    pd.DataFrame(entropy).to_csv(
        output / "entropy_correlations.csv", index=False
    )
    approval.to_csv(output / "threshold_approval.csv", index=False)
    manifest = {
        "schema_version": "fairai.expanded_analysis.v1",
        "evidence_type": "derived",
        "inputs": inputs,
        "statistics": {
            "confidence_interval": "two-sided 95% Student t",
            "paired_primary": "paired t test",
            "paired_robustness": "Wilcoxon signed-rank",
            "multiple_testing": "Holm across expanded paired tests",
            "entropy_correlation": "Spearman rank",
        },
        "outputs": {},
    }
    for path in sorted(output.glob("*.csv")):
        manifest["outputs"][path.name] = sha256_file(path)
    (output / "analysis_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mlp", required=True)
    parser.add_argument("--scaling", required=True)
    parser.add_argument("--heterogeneity", required=True)
    parser.add_argument("--threshold", required=True)
    parser.add_argument("--adversarial", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(analyze(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
