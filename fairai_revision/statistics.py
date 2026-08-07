import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from .manifest import sha256_file, utc_now


METRICS = (
    "accuracy",
    "macro_f1",
    "demographic_parity_gap",
    "equal_opportunity_gap",
    "equalized_odds_gap",
    "subgroup_accuracy_gap",
    "runtime_ms",
)

BOOTSTRAP_REPETITIONS = 10_000
BOOTSTRAP_SEED = 20_260_731


def _write_csv(path, rows):
    if not rows:
        raise ValueError(f"Refusing to write empty statistics table: {path}")
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _holm_adjust(p_values):
    order = np.argsort(p_values)
    adjusted = np.empty(len(p_values), dtype=float)
    running = 0.0
    count = len(p_values)
    for rank, index in enumerate(order):
        candidate = min(1.0, (count - rank) * p_values[index])
        running = max(running, candidate)
        adjusted[index] = running
    return adjusted


def _stable_seed(*parts):
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return BOOTSTRAP_SEED ^ int.from_bytes(digest[:8], "big")


def bootstrap_mean_ci(values, *, seed, repetitions=BOOTSTRAP_REPETITIONS):
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        raise ValueError("Bootstrap confidence interval requires observations")
    if values.size == 1 or np.allclose(values, values[0]):
        value = float(values.mean())
        return value, value
    rng = np.random.default_rng(seed)
    sampled = rng.choice(values, size=(repetitions, values.size), replace=True)
    means = sampled.mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return float(low), float(high)


def paired_rank_biserial(differences):
    differences = np.asarray(differences, dtype=float)
    nonzero = differences[~np.isclose(differences, 0)]
    if nonzero.size == 0:
        return 0.0
    ranks = stats.rankdata(np.abs(nonzero))
    positive = ranks[nonzero > 0].sum()
    negative = ranks[nonzero < 0].sum()
    return float((positive - negative) / ranks.sum())


def summarize(frame):
    rows = []
    grouped = frame.groupby(["scenario_id", "partition", "method"], sort=True)
    for (scenario_id, partition, method), group in grouped:
        for metric in METRICS:
            values = group[metric].dropna().to_numpy(dtype=float)
            if len(values) == 0:
                continue
            mean = float(values.mean())
            std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            ci_low, ci_high = bootstrap_mean_ci(
                values,
                seed=_stable_seed(scenario_id, partition, method, metric),
            )
            rows.append(
                {
                    "scenario_id": scenario_id,
                    "partition": partition,
                    "method": method,
                    "metric": metric,
                    "n": len(values),
                    "mean": mean,
                    "std": std,
                    "median": float(np.median(values)),
                    "ci95_low": ci_low,
                    "ci95_high": ci_high,
                    "minimum": float(values.min()),
                    "maximum": float(values.max()),
                }
            )
    return rows


def paired_b3_vs_b0(frame):
    rows = []
    for (scenario_id, partition), group in frame.groupby(
        ["scenario_id", "partition"], sort=True
    ):
        for metric in METRICS[:-1]:
            pivot = group.pivot(index="seed", columns="method", values=metric)
            if "B0" not in pivot or "B3" not in pivot:
                continue
            paired = pivot[["B0", "B3"]].dropna()
            if len(paired) < 2:
                continue
            differences = paired["B3"].to_numpy() - paired["B0"].to_numpy()
            if np.allclose(differences, differences[0]):
                t_statistic = 0.0 if np.isclose(differences[0], 0) else (
                    math.inf if differences[0] > 0 else -math.inf
                )
                t_p = 1.0 if np.isclose(differences[0], 0) else 0.0
            else:
                t_result = stats.ttest_rel(paired["B3"], paired["B0"])
                t_statistic = float(t_result.statistic)
                t_p = float(t_result.pvalue)
            if np.allclose(differences, 0):
                wilcoxon_statistic, wilcoxon_p = 0.0, 1.0
            else:
                wilcoxon = stats.wilcoxon(paired["B3"], paired["B0"])
                wilcoxon_statistic = float(wilcoxon.statistic)
                wilcoxon_p = float(wilcoxon.pvalue)
            difference_std = differences.std(ddof=1)
            effect = (
                None
                if np.isclose(difference_std, 0) and not np.isclose(differences.mean(), 0)
                else 0.0
                if np.isclose(difference_std, 0)
                else float(differences.mean() / difference_std)
            )
            rows.append(
                {
                    "scenario_id": scenario_id,
                    "partition": partition,
                    "comparison": "B3-B0",
                    "metric": metric,
                    "n": len(paired),
                    "mean_difference": float(differences.mean()),
                    "paired_effect_size_dz": effect,
                    "rank_biserial_correlation": paired_rank_biserial(
                        differences
                    ),
                    "paired_t_statistic": t_statistic,
                    "paired_t_p": t_p,
                    "wilcoxon_statistic": wilcoxon_statistic,
                    "wilcoxon_p": wilcoxon_p,
                }
            )
    adjusted = _holm_adjust([row["paired_t_p"] for row in rows])
    for row, value in zip(rows, adjusted):
        row["paired_t_p_holm"] = float(value)
    return rows


def analyze(input_dirs, output_dir):
    input_dirs = [Path(path) for path in input_dirs]
    frames = []
    inputs = []
    for directory in input_dirs:
        metrics_path = directory / "metrics" / "test_metrics.csv"
        manifest_path = directory / "manifests" / "run_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["completion_status"] != "completed" or manifest["dirty_tree"]:
            raise ValueError(f"Input run is not a clean completed run: {directory}")
        frame = pd.read_csv(metrics_path)
        frames.append(frame)
        inputs.append(
            {
                "run_id": manifest["run_id"],
                "git_commit": manifest["git_commit"],
                "configuration_hash": manifest["configuration_hash"],
                "metrics_sha256": sha256_file(metrics_path),
                "rows": len(frame),
            }
        )
    combined = pd.concat(frames, ignore_index=True)
    if combined.duplicated(["scenario_id", "seed", "partition", "method"]).any():
        raise ValueError("Duplicate paired-result keys")
    summary_rows = summarize(combined)
    paired_rows = paired_b3_vs_b0(combined)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_csv(output_dir / "summary_statistics.csv", summary_rows)
    _write_csv(output_dir / "paired_tests.csv", paired_rows)
    combined.to_csv(output_dir / "combined_test_metrics.csv", index=False)
    manifest = {
        "schema_version": "fairai.statistical_analysis.v1",
        "created_at": utc_now(),
        "evidence_type": "derived",
        "inputs": inputs,
        "input_rows": len(combined),
        "summary_rows": len(summary_rows),
        "paired_test_rows": len(paired_rows),
        "confidence_interval": (
            "two-sided percentile bootstrap 95% CI of the mean; "
            f"{BOOTSTRAP_REPETITIONS} deterministic resamples"
        ),
        "paired_primary_test": "paired t test",
        "paired_robustness_test": "Wilcoxon signed-rank",
        "multiple_testing_correction": "Holm across reported paired t tests",
        "output_hashes": {},
    }
    for filename in (
        "summary_statistics.csv",
        "paired_tests.csv",
        "combined_test_metrics.csv",
    ):
        manifest["output_hashes"][filename] = sha256_file(output_dir / filename)
    (output_dir / "analysis_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description="Analyze paired FairAI core results")
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(analyze(args.input, args.output), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
