from pathlib import Path

import pandas as pd


ROOT = Path("outputs/major_revision")
CSV = ROOT / "primary_csv"
OUTPUT = ROOT / "latex_tables"


def export(name, frame, columns=None):
    if columns:
        frame = frame[columns]
    def latex(value):
        if pd.isna(value):
            return ""
        if isinstance(value, float):
            value = f"{value:.4f}"
        replacements = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
        }
        return "".join(replacements.get(character, character) for character in str(value))

    alignment = "".join(
        "r" if pd.api.types.is_numeric_dtype(frame[column]) else "l"
        for column in frame.columns
    )
    lines = [
        rf"\begin{{tabular}}{{{alignment}}}",
        r"\toprule",
        " & ".join(latex(column) for column in frame.columns) + r" \\",
        r"\midrule",
    ]
    lines.extend(
        " & ".join(latex(value) for value in row) + r" \\"
        for row in frame.itertuples(index=False, name=None)
    )
    lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    text = "\n".join(lines)
    (OUTPUT / f"{name}.tex").write_text(text, encoding="utf-8")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    export(
        "experiment_matrix",
        pd.read_csv(CSV / "Experiment_Matrix.csv"),
        ["scenario_id", "dataset", "model", "clients", "rounds", "seeds"],
    )
    export(
        "datasets_models_partitions",
        pd.read_csv(CSV / "Dataset_Summary.csv"),
        ["dataset", "task", "primary_protected_attribute"],
    )
    baseline = pd.read_csv(CSV / "Baseline_Comparison.csv")
    export(
        "baseline_comparison",
        baseline[baseline["metric"].isin(["accuracy", "equalized_odds_gap"])],
        ["scenario_id", "partition", "method", "metric", "n", "mean", "ci95_low", "ci95_high"],
    )
    export(
        "fairness_sensitivity",
        pd.read_csv(ROOT / "threshold_approval.csv"),
    )
    export(
        "trust_and_proof_claims",
        pd.read_csv(ROOT / "security-evidence" / "attack_matrix.csv").query(
            "scenario in ['A1_invalid_groth16_proof', 'A12_false_metric_reporting', 'A13_metrics_modified_after_proof', 'A14_compromised_authorized_verifier']"
        ),
        ["scenario", "detected", "rejected", "limitation", "evidence_type"],
    )
    export(
        "ipfs_and_stage_overhead",
        pd.read_csv(ROOT / "complexity" / "stage_timing.csv"),
        ["stage", "status", "evidence_type", "n", "mean_ms", "median_ms", "p95_ms"],
    )
    export(
        "attack_outcomes",
        pd.read_csv(ROOT / "descriptive_statistics.csv").query(
            "suite == 'adversarial' and metric in ['accuracy', 'equalized_odds_gap']"
        ),
        ["attack_type", "method", "metric", "n", "mean", "ci95_low", "ci95_high"],
    )
    export(
        "scalability_and_gas",
        pd.read_csv(ROOT / "gas_by_function.csv").query(
            "operation in ['submit_model', 'publish_global_model']"
        ),
        ["batch_size", "operation", "n", "mean_gas", "median_gas", "min_gas", "max_gas"],
    )


if __name__ == "__main__":
    main()
