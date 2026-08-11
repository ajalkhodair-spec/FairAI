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
    "Policy_Approval",
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
    "Stage_Timing",
    "Representation_Fairness",
    "Trust_Boundary",
    "Statistics",
    "Paired_Inference",
    "Scaling_Summary",
    "Missing_Data",
    "Claims_Supported",
    "Reviewer_Evidence_Map",
]


def read_csv(path):
    return pd.read_csv(path)


def records(frame):
    return json.loads(frame.to_json(orient="records"))


def write_workbook_payload(root, workbook):
    missing = [sheet for sheet in SHEETS if sheet not in workbook]
    if missing:
        raise ValueError(f"missing workbook sheets: {', '.join(missing)}")
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


def read_blockers(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| BLK-"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(
            dict(
                zip(
                    ["id", "status", "scope", "blocker", "effect"],
                    cells,
                    strict=True,
                )
            )
        )
    return pd.DataFrame(rows)


def flatten_trust_boundary(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    false_metric = payload["false_metric_reporting"]
    unavailable = payload["approved_artifact_unavailable"]
    return pd.DataFrame(
        [
            {
                "scenario": "false_metric_reporting",
                "expected_control": "proof binds supplied metrics",
                "observed_result": "fabricated metrics approved and aggregated",
                "round_state": false_metric["round_final_state"],
                "on_chain_approved": false_metric["on_chain_approved"],
                "aggregated": false_metric["aggregated"],
                "reason": payload["claim_boundary"],
                "evidence_type": payload["evidence_type"],
                "source_file": str(path),
            },
            {
                "scenario": "approved_artifact_unavailable",
                "expected_control": "fail closed before aggregation",
                "observed_result": "round cancelled and no global model published",
                "round_state": unavailable["final_state"],
                "on_chain_approved": True,
                "aggregated": unavailable["aggregation_started"],
                "reason": unavailable["reason"],
                "evidence_type": payload["evidence_type"],
                "source_file": str(path),
            },
        ]
    )


def flatten_proof_benchmark(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for stage, values in payload["timings_ms"].items():
        rows.append(
            {
                "run_id": payload["run_id"],
                "stage": stage,
                "n": payload["repetitions"],
                "mean_ms": values["mean"],
                "std_ms": values["standard_deviation"],
                "median_ms": values["median"],
                "p95_ms": values["p95_nearest_rank_index"],
                "minimum_ms": values["minimum"],
                "maximum_ms": values["maximum"],
                "valid_proofs_verified": payload["valid_proofs_verified"],
                "negative_cases_rejected": payload["negative_cases_rejected"],
                "setup_type": payload["setup_type"],
                "production_ceremony_required": payload[
                    "production_ceremony_required"
                ],
                "evidence_type": payload["evidence_type"],
                "source_file": str(path),
            }
        )
    return pd.DataFrame(rows)


def summarize_policy_approval_frame(rounds, run_id, source):
    rounds = rounds[
        (rounds["scenario_id"] == "threshold_sensitivity")
        & (rounds["method"] == "B3")
    ].copy()
    rows = []
    scopes = {
        "all_five_rounds": rounds,
        "final_round": rounds[rounds["round"] == rounds["round"].max()],
    }
    for scope, frame in scopes.items():
        for policy_profile, values in frame.groupby("policy_profile", sort=True):
            approval = values["approval_rate"]
            rows.append(
                {
                    "run_id": run_id,
                    "policy_profile": policy_profile,
                    "aggregation_scope": scope,
                    "seed_count": int(values["seed"].nunique()),
                    "round_observations": int(len(values)),
                    "mean_approval_rate": approval.mean(),
                    "std_approval_rate": approval.std(),
                    "minimum_approval_rate": approval.min(),
                    "maximum_approval_rate": approval.max(),
                    "evidence_type": "derived_from_measured_rounds",
                    "source_file": str(source),
                }
            )
    return pd.DataFrame(rows)


def summarize_policy_approval(path, run_id):
    return summarize_policy_approval_frame(read_csv(path), run_id, path)


def summarize_scaling(path, run_id):
    frame = read_csv(path)
    result = frame[
        (frame["suite"] == "scaling") & (frame["metric"] == "runtime_ms")
    ].copy()
    result.insert(0, "run_id", run_id)
    result["evidence_type"] = "derived_from_measured_runs"
    result["source_file"] = str(path)
    return result


def paired_inference(core_path, expanded_path, fairfed_path):
    frames = []
    for analysis_family, path in (
        ("core_logistic", core_path),
        ("expanded_sensitivity", expanded_path),
        ("fairfed_scaling", fairfed_path),
    ):
        frame = read_csv(path).rename(columns={"scenario_id": "suite"})
        frame.insert(0, "analysis_family", analysis_family)
        frame["evidence_type"] = "derived_from_paired_measured_runs"
        frame["source_file"] = str(path)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False)


def annotate_attack_evidence(frame):
    result = frame.copy()
    superseded = {
        "A1_invalid_groth16_proof": (
            "historical_superseded",
            "Current V2 Groth16 proof and negative-case evidence is in Proof_Overhead and Proof_Semantics.",
        ),
        "A7_ipfs_artifact_unavailable": (
            "historical_superseded",
            "Current real Kubo outage/recovery and unavailable-approved-artifact evidence is in IPFS_Availability and Trust_Boundary.",
        ),
        "A8_ipfs_artifact_tampering": (
            "historical_superseded",
            "Current strict byte-verification evidence is in the Kubo full-path archive.",
        ),
        "A9_random_weight_poisoning": (
            "historical_extended",
            "The five-seed algorithmic result remains valid and is extended by the strict B4/B7 Kubo/V2 poisoning suite.",
        ),
        "A10_sign_flip_poisoning": (
            "historical_extended",
            "The five-seed algorithmic result remains valid and is extended by the strict B4/B7 Kubo/V2 poisoning suite.",
        ),
    }
    result["evidence_epoch"] = "current"
    result["current_interpretation"] = "Current bounded evidence; retain the stated limitation."
    for scenario, (epoch, interpretation) in superseded.items():
        mask = result["scenario"] == scenario
        result.loc[mask, "evidence_epoch"] = epoch
        result.loc[mask, "current_interpretation"] = interpretation
    return result


def experiment_matrix():
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
    return pd.DataFrame(configs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="outputs/major_revision")
    parser.add_argument(
        "--primary-csv-only",
        action="store_true",
        help="rebuild workbook_payload.json from the published primary_csv sheets",
    )
    parser.add_argument("--gas-run", default="gas-v2-30rep-4a08a15")
    parser.add_argument(
        "--analysis-dir",
        default="outputs/revision_audit/expanded-analysis-6df6bfb",
    )
    parser.add_argument(
        "--fairfed-analysis-dir",
        default="outputs/revision_audit/fairfed-scaling-analysis",
    )
    parser.add_argument(
        "--infrastructure-analysis-dir",
        default="outputs/revision_audit/infrastructure-analysis-v2",
    )
    parser.add_argument(
        "--stage-timing-dir",
        default="outputs/revision_audit/stage-timing-1536b13",
    )
    parser.add_argument(
        "--entropy-analysis-dir",
        default="outputs/revision_audit/entropy-approval-4d97043",
    )
    parser.add_argument(
        "--trust-boundary-file",
        default="outputs/revision_audit/trust-boundary-1536b13/evidence.json",
    )
    parser.add_argument(
        "--core-analysis-run", default="core-statistics-bootstrap"
    )
    args = parser.parse_args()
    root = Path(args.output_root)
    csv_root = root / "primary_csv"
    csv_root.mkdir(parents=True, exist_ok=True)
    if args.primary_csv_only:
        workbook = {
            sheet: read_csv(csv_root / f"{sheet}.csv")
            for sheet in SHEETS
            if (csv_root / f"{sheet}.csv").exists()
        }
        workbook["Experiment_Matrix"] = experiment_matrix()
        workbook["Policy_Approval"] = summarize_policy_approval_frame(
            workbook["Global_Metrics"],
            "threshold-sensitivity-10seed-aa165b3",
            "outputs/major_revision/primary_csv/Global_Metrics.csv",
        )
        workbook["Paired_Inference"] = paired_inference(
            Path("outputs/major_revision/core-statistics-bootstrap/paired_tests.csv"),
            Path(args.analysis_dir) / "paired_tests.csv",
            Path(args.fairfed_analysis_dir) / "paired_tests.csv",
        )
        workbook["Scaling_Summary"] = summarize_scaling(
            Path(args.fairfed_analysis_dir) / "descriptive_statistics.csv",
            Path(args.fairfed_analysis_dir).name,
        )
        workbook["Adversarial_Results"] = annotate_attack_evidence(
            workbook["Adversarial_Results"].drop(
                columns=["evidence_epoch", "current_interpretation"],
                errors="ignore",
            )
        )
        workbook["README"] = pd.concat(
            [
                workbook["README"][
                    ~workbook["README"]["item"].isin(
                        ["Workbook role", "Figure sheets", "Result presentation sheets", "Azure status"]
                    )
                ],
                pd.DataFrame(
                    [
                        ["Workbook role", "Consolidated publication view derived from canonical CSV evidence"],
                        ["Result presentation sheets", "Twenty formula-backed reviewer-result presentation sheets; 43 canonical evidence sheets remain the data source"],
                        ["Azure status", "Configured and validated as infrastructure code; not executed or measured"],
                    ],
                    columns=["item", "value"],
                ),
            ],
            ignore_index=True,
        )
        for sheet in (
            "README",
            "Experiment_Matrix",
            "Adversarial_Results",
            "Policy_Approval",
            "Paired_Inference",
            "Scaling_Summary",
        ):
            workbook[sheet].to_csv(
                csv_root / f"{sheet}.csv", index=False, quoting=csv.QUOTE_MINIMAL
            )
        write_workbook_payload(root, workbook)
        return

    runs = {
        "adult_core": root / "adult-core-10seed-e01b72a",
        "compas_core": root / "compas-core-10seed-e01b72a",
        "mlp": root / "adult-mlp-b0-b3-b5-5seed-dbc1e53",
        "scaling": root / "client-scaling-5seed-2d2b220",
        "heterogeneity": root / "heterogeneity-b0-b3-10seed-76828c3",
        "threshold": root / "threshold-sensitivity-10seed-aa165b3",
        "adversarial": root / "adversarial-5seed-e8733cb",
        "gas": root / args.gas_run,
        "legacy": root / "legacy_mvp",
    }
    analysis_root = Path(args.analysis_dir)
    fairfed_analysis_root = Path(args.fairfed_analysis_dir)
    infrastructure_analysis_root = Path(args.infrastructure_analysis_dir)
    stage_timing_root = Path(args.stage_timing_dir)
    entropy_analysis_root = Path(args.entropy_analysis_dir)
    trust_boundary_file = Path(args.trust_boundary_file)
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
            ["IPFS status", "Measured on two native Kubo 0.29.0 peers with 30 repetitions"],
            ["V2 proof status", "Thirty valid proofs verified and six negative cases rejected; production ceremony still required"],
            ["FairFed status", "Published stateful weighting rule implemented and evaluated on Adult and COMPAS"],
            ["Source of truth", "Run manifests and source_file columns"],
            ["Workbook role", "Consolidated publication view derived from canonical CSV evidence"],
            ["Result presentation sheets", "Twenty formula-backed reviewer-result presentation sheets; 43 canonical evidence sheets remain the data source"],
            ["Azure status", "Configured and validated as infrastructure code; not executed or measured"],
        ],
        columns=["item", "value"],
    )

    workbook["Experiment_Matrix"] = experiment_matrix()

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
    workbook["FairFed_Comparison"] = add_trace(
        read_csv(fairfed_analysis_root / "descriptive_statistics.csv"),
        fairfed_analysis_root.name,
        "derived_from_measured_runs",
        str(fairfed_analysis_root / "descriptive_statistics.csv"),
    )
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
    workbook["Policy_Approval"] = summarize_policy_approval(
        runs["threshold"] / "metrics" / "fairness_metrics_global.csv",
        runs["threshold"].name,
    )
    workbook["Convergence"] = workbook["Global_Metrics"]
    workbook["Proof_Overhead"] = flatten_proof_benchmark(
        Path("outputs/revision_audit/v2_proof_benchmark.json")
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
    ipfs_sequential = read_csv(infrastructure_analysis_root / "ipfs_sequential.csv")
    for sheet in (
        "IPFS_Add",
        "IPFS_Pin",
        "IPFS_Cold_Retrieval",
        "IPFS_Warm_Retrieval",
    ):
        workbook[sheet] = add_trace(
            ipfs_sequential,
            infrastructure_analysis_root.name,
            "derived_from_30_repeat_native_kubo_measurements",
            str(infrastructure_analysis_root / "ipfs_sequential.csv"),
        )
    workbook["IPFS_Availability"] = add_trace(
        read_csv(infrastructure_analysis_root / "ipfs_recovery.csv"),
        infrastructure_analysis_root.name,
        "derived_from_30_repeat_native_kubo_measurements",
        str(infrastructure_analysis_root / "ipfs_recovery.csv"),
    )
    workbook["IPFS_Concurrency"] = add_trace(
        read_csv(infrastructure_analysis_root / "ipfs_concurrency.csv"),
        infrastructure_analysis_root.name,
        "derived_from_30_repeat_native_kubo_measurements",
        str(infrastructure_analysis_root / "ipfs_concurrency.csv"),
    )

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
        annotate_attack_evidence(
            read_csv(root / "security-evidence" / "attack_matrix.csv")
        ),
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
    workbook["Stage_Timing"] = add_trace(
        read_csv(stage_timing_root / "stage_timing.csv"),
        stage_timing_root.name,
        "derived_from_independently_instrumented_stages",
        str(stage_timing_root / "stage_timing.csv"),
    )
    workbook["Representation_Fairness"] = add_trace(
        read_csv(entropy_analysis_root / "representation_fairness.csv"),
        entropy_analysis_root.name,
        "derived_from_measured_client_decisions",
        str(entropy_analysis_root / "representation_fairness.csv"),
    )
    workbook["Trust_Boundary"] = flatten_trust_boundary(trust_boundary_file)
    workbook["Statistics"] = add_trace(
        read_csv(analysis_root / "experiment_summary.csv"),
        analysis_root.name,
        "derived",
        str(analysis_root / "experiment_summary.csv"),
    )
    workbook["Paired_Inference"] = paired_inference(
        core_analysis_root / "paired_tests.csv",
        analysis_root / "paired_tests.csv",
        fairfed_analysis_root / "paired_tests.csv",
    )
    workbook["Scaling_Summary"] = summarize_scaling(
        fairfed_analysis_root / "descriptive_statistics.csv",
        fairfed_analysis_root.name,
    )
    blockers = read_blockers(Path("BLOCKERS.md"))
    workbook["Missing_Data"] = blockers

    claims = pd.DataFrame(
        [
            ["Adult and COMPAS loaders are checksum pinned", "supported", "dataset_manifest"],
            ["LR and small MLP execute federated rounds", "supported", "measured"],
            ["3/5/10/20 clients are evaluated", "supported_B0", "measured"],
            ["Fairness policy changes approval and outcomes", "supported_B3", "measured"],
            ["Random-weight poisoning is mitigated by coordinate median in this suite", "supported_bounded", "measured"],
            ["Direct V2 Groth16 is measured locally", "supported_bounded", "measured_local"],
            ["Two-peer native Kubo overhead is measured", "supported_bounded", "measured_local"],
            ["Published FairFed server weighting is compared", "supported_bounded", "measured"],
            ["Proofs establish correct derivation of private metrics", "not_supported", "trust_boundary_test"],
            ["Approved artifacts fail closed when unavailable", "supported_bounded", "full_path_test"],
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
        "stage_timing.csv": workbook["Stage_Timing"],
        "representation_fairness.csv": workbook["Representation_Fairness"],
        "trust_boundary.csv": workbook["Trust_Boundary"],
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
        "ipfs_recovery.csv": workbook["IPFS_Availability"],
        "ipfs_concurrency.csv": workbook["IPFS_Concurrency"],
        "ipfs_artifact_sizes.csv": workbook["IPFS_Add"][[
            "run_id", "payload_bytes", "evidence_type", "source_file"
        ]].drop_duplicates(),
        "filesystem_baseline.csv": missing_frame(
            "LIMITATION", "paired filesystem baseline not measured"
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

    write_workbook_payload(root, workbook)
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
