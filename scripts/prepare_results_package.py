import argparse
import csv
import json
from pathlib import Path

import pandas as pd


SHEETS = [
    "README",
    "Experiment_Matrix",
    "Run_Manifest",
    "Legacy_Baseline",
    "Dataset_Summary",
    "Client_Partitions",
    "Entropy",
    "Local_Metrics",
    "Global_Metrics",
    "Baseline_Comparison",
    "FairFed_Comparison",
    "Scaling",
    "Heterogeneity",
    "Threshold_Sensitivity",
    "Convergence",
    "Proof_Overhead",
    "Proof_Semantics",
    "Verifier_Security",
    "IPFS_Add",
    "IPFS_Pin",
    "IPFS_Cold_Retrieval",
    "IPFS_Warm_Retrieval",
    "IPFS_Availability",
    "IPFS_Concurrency",
    "Gas_By_Function",
    "Gas_Batching",
    "Cost_Scenarios",
    "Adversarial_Results",
    "Poisoning",
    "False_Metrics",
    "Privacy_Exposure",
    "Ethics_Scope",
    "Complexity",
    "Statistics",
    "Missing_Data",
    "Claims_Supported",
    "Reviewer_Evidence_Map",
]


def read_csv(path):
    return pd.read_csv(path)


def records(frame):
    return json.loads(frame.to_json(orient="records"))


def add_trace(frame, run_id, evidence_type, source):
    result = frame.copy()
    if "run_id" not in result:
        result.insert(0, "run_id", run_id)
    result["evidence_type"] = evidence_type
    result["source_file"] = source
    return result


def concat_csv(paths, evidence_type="measured"):
    frames = []
    for run_id, path in paths:
        frame = read_csv(path)
        frames.append(add_trace(frame, run_id, evidence_type, str(path)))
    return pd.concat(frames, ignore_index=True)


def flatten_manifest(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "run_id": payload["run_id"],
        "scenario_id": payload["scenario_id"],
        "git_commit": payload["git_commit"],
        "configuration_hash": payload["configuration_hash"],
        "dataset_checksum": payload["dataset_checksum"],
        "partition_checksum": payload["partition_checksum"],
        "completion_status": payload["completion_status"],
        "dirty_tree": payload["dirty_tree"],
        "start_timestamp": payload["start_timestamp"],
        "end_timestamp": payload["end_timestamp"],
        "evidence_type": "manifest",
        "source_file": str(path),
    }


def missing_frame(blocker, scope):
    return pd.DataFrame(
        [
            {
                "status": "blocked",
                "scope": scope,
                "value": None,
                "blocker": blocker,
                "evidence_type": "missing",
                "source_file": "BLOCKERS.md",
            }
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="outputs/major_revision")
    parser.add_argument(
        "--gas-run", default="gas-throughput-30rep-7dff9b5"
    )
    parser.add_argument(
        "--analysis-run", default="expanded-analysis-bootstrap-aae4091"
    )
    parser.add_argument(
        "--core-analysis-run", default="core-statistics-bootstrap"
    )
    args = parser.parse_args()
    root = Path(args.output_root)
    csv_root = root / "primary_csv"
    csv_root.mkdir(parents=True, exist_ok=True)

    runs = {
        "adult_core": root / "adult-core-10seed-e01b72a",
        "compas_core": root / "compas-core-10seed-e01b72a",
        "mlp": root / "adult-mlp-5seed-ee23a65",
        "scaling": root / "client-scaling-5seed-2d2b220",
        "heterogeneity": root / "heterogeneity-10seed-2d2b220",
        "threshold": root / "threshold-sensitivity-10seed-aa165b3",
        "adversarial": root / "adversarial-5seed-e8733cb",
        "gas": root / args.gas_run,
        "legacy": root / "legacy_mvp",
    }
    analysis_root = root / args.analysis_run
    core_analysis_root = root / args.core_analysis_run
    measured_runs = [
        "adult_core",
        "compas_core",
        "mlp",
        "scaling",
        "heterogeneity",
        "threshold",
        "adversarial",
    ]

    workbook = {}
    workbook["README"] = pd.DataFrame(
        [
            ["Purpose", "Traceable FairAI major-revision evidence package"],
            ["Evidence boundary", "Measured, derived, modeled, tested, blocked, and missing are distinguished"],
            ["Primary datasets", "Adult and COMPAS"],
            ["Core models", "Federated logistic regression and small MLP"],
            ["IPFS status", "Two-peer benchmark code complete; measurement blocked by Docker socket access"],
            ["V2 proof status", "Binding and verifier tests complete; direct V2 artifacts blocked by Circom version"],
            ["FairFed status", "Blocked; no heuristic substitution"],
            ["Source of truth", "Run manifests and source_file columns"],
        ],
        columns=["item", "value"],
    )

    configs = []
    for path in sorted(Path("configs/revision").glob("*.yaml")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        configs.append(
            {
                "scenario_id": payload["scenario_id"],
                "executor": payload["executor"],
                "dataset": payload["dataset"],
                "model": payload["model"],
                "clients": payload["clients"],
                "rounds": payload["rounds"],
                "method": payload["method"],
                "seeds": payload.get("seeds", 1),
                "evidence_type": payload["evidence_type"],
                "source_file": str(path),
            }
        )
    workbook["Experiment_Matrix"] = pd.DataFrame(configs)

    manifest_paths = [
        runs[name] / "manifests" / "run_manifest.json"
        for name in measured_runs + ["gas", "legacy"]
    ]
    workbook["Run_Manifest"] = pd.DataFrame(
        [flatten_manifest(path) for path in manifest_paths]
    )
    workbook["Legacy_Baseline"] = add_trace(
        read_csv(runs["legacy"] / "global_metrics.csv"),
        "legacy_mvp",
        "measured_legacy",
        str(runs["legacy"] / "global_metrics.csv"),
    )
    workbook["Dataset_Summary"] = pd.DataFrame(
        [
            {
                "dataset": "Adult",
                "task": "income classification",
                "primary_protected_attribute": "sex",
                "source_checksum_manifest": "data/raw/adult/download_manifest.json",
                "evidence_type": "dataset_manifest",
                "source_file": "data/raw/adult/download_manifest.json",
            },
            {
                "dataset": "COMPAS",
                "task": "two-year recidivism classification",
                "primary_protected_attribute": "race",
                "source_checksum_manifest": "data/raw/compas/download_manifest.json",
                "evidence_type": "dataset_manifest",
                "source_file": "data/raw/compas/download_manifest.json",
            },
        ]
    )

    partition_frames = []
    entropy_frames = []
    for path in sorted((runs["heterogeneity"] / "partitions").glob("**/partition_summary.csv")):
        frame = read_csv(path)
        frame["source_file"] = str(path)
        frame["evidence_type"] = "measured"
        partition_frames.append(frame)
    for path in sorted((runs["heterogeneity"] / "partitions").glob("**/entropy_by_client.csv")):
        frame = read_csv(path)
        frame["seed"] = int(path.parts[-4].removeprefix("seed_"))
        frame["partition"] = path.parent.name
        frame["source_file"] = str(path)
        frame["evidence_type"] = "measured"
        entropy_frames.append(frame)
    workbook["Client_Partitions"] = pd.concat(partition_frames, ignore_index=True)
    workbook["Entropy"] = pd.concat(entropy_frames, ignore_index=True)

    workbook["Local_Metrics"] = concat_csv(
        [
            (runs[name].name, runs[name] / "metrics" / "fairness_metrics_by_client.csv")
            for name in measured_runs
        ]
    )
    workbook["Global_Metrics"] = concat_csv(
        [
            (runs[name].name, runs[name] / "metrics" / "fairness_metrics_global.csv")
            for name in measured_runs
        ]
    )
    workbook["Baseline_Comparison"] = add_trace(
        read_csv(core_analysis_root / "summary_statistics.csv"),
        core_analysis_root.name,
        "derived",
        str(core_analysis_root / "summary_statistics.csv"),
    )
    workbook["FairFed_Comparison"] = missing_frame("BLK-003", "B5 FairFed")
    workbook["Scaling"] = add_trace(
        read_csv(runs["scaling"] / "metrics" / "test_metrics.csv"),
        runs["scaling"].name,
        "measured",
        str(runs["scaling"] / "metrics" / "test_metrics.csv"),
    )
    workbook["Heterogeneity"] = add_trace(
        read_csv(runs["heterogeneity"] / "metrics" / "test_metrics.csv"),
        runs["heterogeneity"].name,
        "measured",
        str(runs["heterogeneity"] / "metrics" / "test_metrics.csv"),
    )
    workbook["Threshold_Sensitivity"] = add_trace(
        read_csv(runs["threshold"] / "metrics" / "test_metrics.csv"),
        runs["threshold"].name,
        "measured_B3_policy_effect",
        str(runs["threshold"] / "metrics" / "test_metrics.csv"),
    )
    workbook["Convergence"] = workbook["Global_Metrics"]
    proof_legacy = add_trace(
        read_csv(runs["legacy"] / "proof_timings.csv"),
        "legacy_mvp",
        "measured_legacy",
        str(runs["legacy"] / "proof_timings.csv"),
    )
    workbook["Proof_Overhead"] = pd.concat(
        [proof_legacy, missing_frame("BLK-001", "direct V2 Groth16")],
        ignore_index=True,
    )
    workbook["Proof_Semantics"] = add_trace(
        read_csv(root / "security-evidence" / "false_metric_reporting_results.csv"),
        "security-evidence",
        "analytical_and_tested",
        str(root / "security-evidence" / "false_metric_reporting_results.csv"),
    )
    workbook["Verifier_Security"] = pd.concat(
        [
            add_trace(
                read_csv(root / "security-evidence" / name),
                "security-evidence",
                "tested",
                str(root / "security-evidence" / name),
            )
            for name in (
                "signature_attack_results.csv",
                "replay_results.csv",
                "compromised_verifier_results.csv",
            )
        ],
        ignore_index=True,
    )
    for sheet, scope in (
        ("IPFS_Add", "two-peer Kubo add"),
        ("IPFS_Pin", "two-peer Kubo pin"),
        ("IPFS_Cold_Retrieval", "two-peer cold retrieval"),
        ("IPFS_Warm_Retrieval", "two-peer warm retrieval"),
        ("IPFS_Availability", "two-peer availability and recovery"),
        ("IPFS_Concurrency", "two-peer concurrent retrieval"),
    ):
        workbook[sheet] = missing_frame("BLK-002", scope)

    gas_summary = add_trace(
        read_csv(runs["gas"] / "blockchain" / "gas_summary.csv"),
        runs["gas"].name,
        "measured_hardhat",
        str(runs["gas"] / "blockchain" / "gas_summary.csv"),
    )
    workbook["Gas_By_Function"] = gas_summary
    workbook["Gas_Batching"] = gas_summary[
        gas_summary["operation"].isin(["submit_model", "publish_global_model"])
    ]
    workbook["Cost_Scenarios"] = add_trace(
        read_csv(runs["gas"] / "derived" / "modeled_transaction_costs.csv"),
        runs["gas"].name,
        "modeled",
        str(runs["gas"] / "derived" / "modeled_transaction_costs.csv"),
    )
    workbook["Adversarial_Results"] = add_trace(
        read_csv(root / "security-evidence" / "attack_matrix.csv"),
        "security-evidence",
        "mixed",
        str(root / "security-evidence" / "attack_matrix.csv"),
    )
    workbook["Poisoning"] = add_trace(
        read_csv(runs["adversarial"] / "metrics" / "test_metrics.csv"),
        runs["adversarial"].name,
        "measured",
        str(runs["adversarial"] / "metrics" / "test_metrics.csv"),
    )
    workbook["False_Metrics"] = workbook["Proof_Semantics"]
    workbook["Privacy_Exposure"] = add_trace(
        read_csv(root / "governance" / "privacy_exposure_inventory.csv"),
        "governance",
        "scope",
        str(root / "governance" / "privacy_exposure_inventory.csv"),
    )
    workbook["Ethics_Scope"] = add_trace(
        read_csv(root / "governance" / "ethics_scope_matrix.csv"),
        "governance",
        "scope",
        str(root / "governance" / "ethics_scope_matrix.csv"),
    )
    workbook["Complexity"] = add_trace(
        read_csv(root / "complexity" / "complexity_analysis.csv"),
        "complexity",
        "analytical",
        str(root / "complexity" / "complexity_analysis.csv"),
    )
    workbook["Statistics"] = add_trace(
        read_csv(analysis_root / "experiment_summary.csv"),
        analysis_root.name,
        "derived",
        str(analysis_root / "experiment_summary.csv"),
    )
    blockers = pd.read_csv(
        "BLOCKERS.md",
        sep="|",
        skiprows=4,
        names=["drop", "id", "scope", "blocker", "effect", "resolution", "drop2"],
        engine="python",
    )[["id", "scope", "blocker", "effect", "resolution"]]
    blockers = blockers[
        blockers["id"].fillna("").str.strip().str.startswith("BLK-")
    ].reset_index(drop=True)
    workbook["Missing_Data"] = blockers.apply(lambda column: column.str.strip())

    claims = pd.DataFrame(
        [
            ["Adult and COMPAS loaders are checksum pinned", "supported", "dataset_manifest"],
            ["LR and small MLP execute federated rounds", "supported", "measured"],
            ["3/5/10/20 clients are evaluated", "supported_B0", "measured"],
            ["Fairness policy changes approval and outcomes", "supported_B3", "measured"],
            ["Random-weight poisoning is mitigated by coordinate median in this suite", "supported_bounded", "measured"],
            ["Direct V2 Groth16 is measured", "not_supported", "blocked"],
            ["Two-peer IPFS overhead is measured", "not_supported", "blocked"],
            ["FairFed is compared", "not_supported", "blocked"],
            ["Raw data locality provides formal privacy", "not_supported", "nonclaim"],
            ["FairAI operationalizes all ethics dimensions", "not_supported", "nonclaim"],
        ],
        columns=["claim", "status", "evidence_type"],
    )
    claims["source_file"] = "outputs/major_revision/claims_supported.json"
    workbook["Claims_Supported"] = claims
    reviewer = pd.read_csv("docs/revision/REVIEWER_GAP_MATRIX.csv")
    reviewer["evidence_type"] = "evidence_map"
    reviewer["source_file"] = "docs/revision/REVIEWER_EVIDENCE_MAP.md"
    workbook["Reviewer_Evidence_Map"] = reviewer

    for sheet in SHEETS:
        frame = workbook[sheet]
        frame.to_csv(csv_root / f"{sheet}.csv", index=False, quoting=csv.QUOTE_MINIMAL)

    exact_csv_exports = {
        "gas_by_function.csv": workbook["Gas_By_Function"],
        "gas_batching.csv": workbook["Gas_Batching"],
        "cost_scenarios.csv": workbook["Cost_Scenarios"],
        "poisoning_results.csv": workbook["Poisoning"],
        "attack_matrix.csv": workbook["Adversarial_Results"],
        "fairness_metrics_by_client.csv": workbook["Local_Metrics"],
        "fairness_metrics_global.csv": workbook["Global_Metrics"],
        "threshold_sensitivity.csv": workbook["Threshold_Sensitivity"],
        "threshold_approval.csv": add_trace(
            read_csv(analysis_root / "threshold_approval.csv"),
            analysis_root.name,
            "derived",
            str(analysis_root / "threshold_approval.csv"),
        ),
        "entropy_by_client.csv": workbook["Entropy"],
        "partition_summary.csv": workbook["Client_Partitions"],
        "entropy_correlations.csv": add_trace(
            read_csv(analysis_root / "entropy_correlations.csv"),
            analysis_root.name,
            "derived",
            str(analysis_root / "entropy_correlations.csv"),
        ),
        "complexity_analysis.csv": workbook["Complexity"],
        "stage_timing.csv": add_trace(
            read_csv(root / "complexity" / "stage_timing.csv"),
            "complexity",
            "measured_and_missing",
            str(root / "complexity" / "stage_timing.csv"),
        ),
        "verifier_security_results.csv": workbook["Verifier_Security"],
    }
    for filename in (
        "descriptive_statistics.csv",
        "confidence_intervals.csv",
        "paired_tests.csv",
        "corrected_p_values.csv",
        "effect_sizes.csv",
    ):
        exact_csv_exports[filename] = add_trace(
            read_csv(analysis_root / filename),
            analysis_root.name,
            "derived",
            str(analysis_root / filename),
        )

    throughput = read_csv(
        runs["gas"] / "blockchain" / "transaction_throughput.csv"
    )
    throughput_summary = (
        throughput.groupby(["mode", "concurrency"], sort=True)
        .agg(
            n=("transactions_per_second", "count"),
            mean_tps=("transactions_per_second", "mean"),
            std_tps=("transactions_per_second", "std"),
            median_tps=("transactions_per_second", "median"),
            p95_tps=(
                "transactions_per_second",
                lambda values: values.quantile(0.95),
            ),
            mean_elapsed_ms=("elapsed_ms", "mean"),
            median_latency_ms=("median_latency_ms", "median"),
            p95_latency_ms=("p95_latency_ms", lambda values: values.quantile(0.95)),
            failure_rate=("failure_rate", "mean"),
            mean_total_gas=("total_gas", "mean"),
        )
        .reset_index()
    )
    exact_csv_exports["transaction_throughput.csv"] = add_trace(
        throughput_summary,
        runs["gas"].name,
        "measured_hardhat",
        str(runs["gas"] / "blockchain" / "transaction_throughput.csv"),
    )

    ipfs_exports = {
        "ipfs_add_latency.csv": workbook["IPFS_Add"],
        "ipfs_pin_latency.csv": workbook["IPFS_Pin"],
        "ipfs_cold_retrieval.csv": workbook["IPFS_Cold_Retrieval"],
        "ipfs_warm_retrieval.csv": workbook["IPFS_Warm_Retrieval"],
        "ipfs_availability.csv": workbook["IPFS_Availability"],
        "ipfs_recovery.csv": missing_frame(
            "BLK-002", "two-peer publisher restart and replica recovery"
        ),
        "ipfs_concurrency.csv": workbook["IPFS_Concurrency"],
        "ipfs_artifact_sizes.csv": missing_frame(
            "BLK-002", "two-peer Kubo artifact size accounting"
        ),
        "filesystem_baseline.csv": missing_frame(
            "BLK-002", "paired filesystem baseline"
        ),
    }
    exact_csv_exports.update(ipfs_exports)

    signature_attacks = read_csv(
        root / "security-evidence" / "signature_attack_results.csv"
    )
    exact_csv_exports["signer_revocation_results.csv"] = add_trace(
        signature_attacks[
            signature_attacks["mutation"] == "revoked_signer"
        ],
        "security-evidence",
        "tested",
        str(root / "security-evidence" / "signature_attack_results.csv"),
    )
    exact_csv_exports["verifier_mode_comparison.csv"] = pd.DataFrame(
        [
            {
                "mode": "single_authorized_verifier",
                "status": "tested",
                "signature_threshold": 1,
                "compromised_single_key_accepted": True,
                "evidence_type": "tested",
                "source_file": (
                    "outputs/major_revision/security-evidence/"
                    "compromised_verifier_results.csv"
                ),
            },
            {
                "mode": "two_of_three_committee",
                "status": "not_implemented_optional",
                "signature_threshold": 2,
                "compromised_single_key_accepted": None,
                "evidence_type": "missing_optional",
                "source_file": "docs/revision/verifier_trust_model.md",
            },
        ]
    )
    entropy_summary = (
        workbook["Entropy"]
        .groupby("partition", dropna=False, sort=True)
        .agg(
            client_rows=("client_id", "count"),
            mean_label_entropy=("label_entropy", "mean"),
            std_label_entropy=("label_entropy", "std"),
            mean_group_entropy=("group_entropy", "mean"),
            std_group_entropy=("group_entropy", "std"),
            mean_sample_count=("sample_count", "mean"),
        )
        .reset_index()
    )
    exact_csv_exports["entropy_summary.csv"] = add_trace(
        entropy_summary,
        runs["heterogeneity"].name,
        "derived",
        str(runs["heterogeneity"] / "partitions"),
    )
    for filename, frame in exact_csv_exports.items():
        frame.to_csv(root / filename, index=False, quoting=csv.QUOTE_MINIMAL)

    attack_records = records(workbook["Adversarial_Results"])
    with (root / "attack_details.jsonl").open("w", encoding="utf-8") as handle:
        for record in attack_records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    policy_profiles = json.loads(
        Path("configs/revision/policy_profiles.json").read_text(
            encoding="utf-8"
        )
    )
    (root / "policy_profiles.json").write_text(
        json.dumps(policy_profiles, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    payload = {
        "schema_version": "fairai.workbook_payload.v1",
        "sheets": {
            sheet: {
                "columns": list(workbook[sheet].columns),
                "rows": records(workbook[sheet]),
            }
            for sheet in SHEETS
        },
    }
    (root / "workbook_payload.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (root / "experiment_summary.json").write_text(
        json.dumps(
            {
                "schema_version": "fairai.experiment_summary.v1",
                "completed_runs": [
                    flatten_manifest(path) for path in manifest_paths
                ],
                "expanded_statistics": records(workbook["Statistics"]),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "claims_supported.json").write_text(
        json.dumps(records(claims), indent=2) + "\n", encoding="utf-8"
    )
    (root / "limitations_observed.json").write_text(
        json.dumps(
            {
                "schema_version": "fairai.limitations.v1",
                "limitations": records(blockers),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "missing_measurements.json").write_text(
        json.dumps(records(blockers), indent=2) + "\n", encoding="utf-8"
    )
    (root / "reviewer_evidence_map.json").write_text(
        json.dumps(records(reviewer), indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
