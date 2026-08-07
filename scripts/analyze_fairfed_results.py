import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analyze_expanded_results import (
    holm_adjust,
    load_completed,
    paired_rows,
    sha256_file,
    summarize,
)


def analyze(args):
    inputs = {}
    frames = {}
    for name in ("adult", "compas", "scaling"):
        frame, evidence = load_completed(Path(getattr(args, name)))
        frames[name] = frame
        inputs[name] = evidence

    summaries = []
    for dataset in ("adult", "compas"):
        summaries.extend(
            summarize(frames[dataset], dataset, ["partition", "method"])
        )
    summaries.extend(
        summarize(frames["scaling"], "scaling", ["client_count", "method"])
    )

    paired = []
    for dataset in ("adult", "compas"):
        paired.extend(
            paired_rows(frames[dataset], dataset, ["partition"], "B0", "B5")
        )
    paired.extend(
        paired_rows(frames["scaling"], "scaling", ["client_count"], "B0", "B5")
    )
    paired.extend(
        paired_rows(frames["scaling"], "scaling", ["client_count"], "B0", "B6")
    )
    holm_adjust(paired)

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    descriptive_path = output / "descriptive_statistics.csv"
    paired_path = output / "paired_tests.csv"
    pd.DataFrame(summaries).to_csv(descriptive_path, index=False)
    pd.DataFrame(paired).to_csv(paired_path, index=False)

    manifest = {
        "schema_version": "fairai.fairfed_scaling_analysis.v1",
        "evidence_type": "derived",
        "analysis_git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "inputs": inputs,
        "statistics": {
            "confidence_interval": "two-sided deterministic percentile bootstrap 95% CI of the mean",
            "paired_primary": "paired t test",
            "paired_robustness": "Wilcoxon signed-rank",
            "effect_sizes": "paired Cohen dz and rank-biserial correlation",
            "multiple_testing": "Holm correction across all reported paired t tests",
            "difference_direction": "right method minus left method; negative fairness gap is favorable",
        },
        "outputs": {
            descriptive_path.name: sha256_file(descriptive_path),
            paired_path.name: sha256_file(paired_path),
        },
        "row_counts": {
            "descriptive_statistics": len(summaries),
            "paired_tests": len(paired),
        },
    }
    (output / "analysis_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), **manifest["row_counts"]}, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Analyze clean FairFed and algorithmic scaling runs"
    )
    parser.add_argument("--adult", required=True)
    parser.add_argument("--compas", required=True)
    parser.add_argument("--scaling", required=True)
    parser.add_argument("--output", required=True)
    analyze(parser.parse_args())


if __name__ == "__main__":
    main()
