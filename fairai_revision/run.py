import argparse
import csv
import json
import statistics
import sys
import time
import traceback
from pathlib import Path

from .config import canonical_json_bytes, config_hash, load_config
from .manifest import (
    new_manifest,
    prepare_output,
    refresh_missing_fields,
    utc_now,
    validate_manifest,
    write_json,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "major_revision"


def experiment_seeds(config):
    seeds = config.get("experiment_seeds", [config["seed"]])
    if not seeds or not all(isinstance(seed, int) for seed in seeds):
        raise ValueError("experiment_seeds must be a nonempty integer list")
    if len(set(seeds)) != len(seeds):
        raise ValueError("experiment_seeds must be unique")
    return seeds


def run_smoke(config, output_dir):
    from scripts.fairai_mvp import evaluate, generate_partition, train_logistic

    data = generate_partition(1, min(config.get("samples_per_client", 40), 80))
    weights = train_logistic(
        data,
        epochs=config["local_epochs"],
        learning_rate=config.get("learning_rate", 0.08),
    )
    metrics = evaluate(weights, data)
    dataset_rows = [
        {"x1": row.x1, "x2": row.x2, "group": row.group, "label": row.label}
        for row in data
    ]
    dataset_bytes = canonical_json_bytes(dataset_rows)
    partition_checksum = __import__("hashlib").sha256(dataset_bytes).hexdigest()

    model = {
        "schema_version": "fairai.model.smoke.v1",
        "type": "logistic_regression",
        "weights": weights,
        "samples": len(data),
    }
    write_json(output_dir / "models" / "client_1.json", model)
    write_json(output_dir / "metrics" / "client_1.json", metrics)
    with (output_dir / "raw" / "client_metrics.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["node_id", "accuracy", "demographic_parity_gap", "equal_opportunity_gap"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "node_id": 1,
                "accuracy": metrics["accuracy"],
                "demographic_parity_gap": metrics["demographic_parity_gap"],
                "equal_opportunity_gap": metrics["equal_opportunity_gap"],
            }
        )
    return {
        "dataset_checksum": partition_checksum,
        "partition_checksum": partition_checksum,
        "summary": {
            "clients_executed": 1,
            "accuracy": metrics["accuracy"],
            "demographic_parity_gap": metrics["demographic_parity_gap"],
        },
    }


def mean(values):
    return statistics.mean(values) if values else None


def write_csv(path, rows, fieldnames):
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def baseline_comparison(config, node_rows, global_rows, gas_rows):
    expected = config.get("expected_baseline", {})
    tolerance = config.get("numeric_tolerance", 1e-4)
    comparisons = []

    def compare(field, observed, expected_value, exact=False):
        difference = abs(float(observed) - float(expected_value))
        matched = difference == 0 if exact else difference <= tolerance
        comparisons.append(
            {
                "field": field,
                "observed": observed,
                "expected": expected_value,
                "absolute_difference": difference,
                "tolerance": 0 if exact else tolerance,
                "matched": matched,
            }
        )

    first_trial_nodes = {str(row["node_id"]): row for row in node_rows if row["trial"] == 1}
    for node_id, values in expected.get("nodes", {}).items():
        observed = first_trial_nodes[node_id]
        compare(
            f"node_{node_id}.accuracy",
            observed["accuracy"],
            values["accuracy"],
        )
        compare(
            f"node_{node_id}.demographic_parity_gap",
            observed["demographic_parity_gap"],
            values["demographic_parity_gap"],
        )
    first_global = next(row for row in global_rows if row["trial"] == 1)
    for field in (
        "approved_nodes",
        "rejected_nodes",
        "global_accuracy",
        "global_demographic_parity_gap",
        "approval_rate",
    ):
        compare(field, first_global[field], expected[field])
    publication = next(row for row in gas_rows if row["trial"] == 1 and row["operation"] == "global_publication")
    compare(
        "global_publication_gas",
        publication["gas_used"],
        expected["global_publication_gas"],
        exact=True,
    )
    return {
        "schema_version": "fairai.legacy_baseline_comparison.v1",
        "numeric_tolerance": tolerance,
        "all_matched": all(row["matched"] for row in comparisons),
        "comparisons": comparisons,
    }


def run_legacy(config, output_dir):
    from scripts.fairai_mvp import run_pipeline

    trials = config.get("trials", 3)
    node_rows = []
    global_rows = []
    gas_rows = []
    artifact_rows = []
    proof_rows = []
    ipfs_rows = []
    lifecycle = []
    trial_manifests = []
    trial_summaries = []

    for trial in range(1, trials + 1):
        trial_id = f"{output_dir.name}-trial-{trial}"
        trial_dir = output_dir / "raw" / f"trial_{trial}"
        started = time.perf_counter()
        trial_manifest = new_manifest(
            config,
            trial_id,
            output_dir.name,
            REPO_ROOT,
        )
        summary = run_pipeline(
            trial_dir,
            force_zk=config.get("force_zk", False),
            require_real_ipfs=config.get("require_real_ipfs", True),
        )
        runtime_ms = round((time.perf_counter() - started) * 1000, 3)
        prepare_output(trial_dir)
        ledger = json.loads((trial_dir / "ledger.json").read_text(encoding="utf-8"))
        records = {record["node_id"]: record for record in ledger["records"]}

        for node in summary["node_results"]:
            row = {
                "run_id": trial_id,
                "trial": trial,
                "seed": config["seed"],
                "node_id": node["node_id"],
                "accuracy": node["accuracy"],
                "demographic_parity_gap": node["demographic_parity_gap"],
                "equal_opportunity_gap": node["equal_opportunity_gap"],
                "proof_verified": node["proof_verified"],
                "approval_status": node["approval_status"],
                "source_file": f"raw/trial_{trial}/metrics.csv",
            }
            node_rows.append(row)
            record = records[node["node_id"]]
            for artifact_type, cid_field in (
                ("model", "model_cid"),
                ("proof", "proof_cid"),
                ("public", "public_cid"),
                ("metadata", "metadata_cid"),
                ("metrics", "metrics_cid"),
                ("manifest", "manifest_cid"),
            ):
                artifact_rows.append(
                    {
                        "run_id": trial_id,
                        "trial": trial,
                        "node_id": node["node_id"],
                        "artifact_type": artifact_type,
                        "cid": record[cid_field],
                        "ipfs_mode": summary["ipfs_mode"],
                        "source_file": f"raw/trial_{trial}/ledger.json",
                    }
                )
            gas_rows.append(
                {
                    "run_id": trial_id,
                    "trial": trial,
                    "operation": "model_submission",
                    "node_id": node["node_id"],
                    "gas_used": int(node["gas_used"]),
                    "source_file": f"raw/trial_{trial}/metrics.csv",
                }
            )

        proof_times = summary["instrumentation"]["proof_generation_ms"]
        for index, proof_ms in enumerate(proof_times, start=1):
            proof_rows.append(
                {
                    "run_id": trial_id,
                    "trial": trial,
                    "node_id": index,
                    "proof_generation_ms": proof_ms,
                    "proof_verified": summary["node_results"][index - 1]["proof_verified"],
                    "source_file": f"raw/trial_{trial}/run_summary.json",
                }
            )
        for index, check in enumerate(
            summary["instrumentation"]["ipfs_retrieval_checks"], start=1
        ):
            ipfs_rows.append(
                {
                    "run_id": trial_id,
                    "trial": trial,
                    "check_index": index,
                    "cid": check["cid"],
                    "mode": check["mode"],
                    "valid": check["valid"],
                    "retrieval_ms": check["retrieval_ms"],
                    "source_file": f"raw/trial_{trial}/run_summary.json",
                }
            )
        for event in summary["round_events"]:
            lifecycle.append({"run_id": trial_id, "trial": trial, **event})

        publication_gas = int(summary["global_publication"]["gas_used"])
        gas_rows.append(
            {
                "run_id": trial_id,
                "trial": trial,
                "operation": "global_publication",
                "node_id": "",
                "gas_used": publication_gas,
                "source_file": f"raw/trial_{trial}/run_summary.json",
            }
        )
        global_row = {
            "run_id": trial_id,
            "trial": trial,
            "seed": config["seed"],
            "approved_nodes": summary["approved_nodes"],
            "rejected_nodes": summary["rejected_nodes"],
            "approval_rate": round(summary["approved_nodes"] / summary["nodes_total"], 6),
            "global_accuracy": summary["global_model"]["validation_metrics"]["accuracy"],
            "global_demographic_parity_gap": summary["global_model"]["validation_metrics"][
                "demographic_parity_gap"
            ],
            "runtime_ms": runtime_ms,
            "source_file": f"raw/trial_{trial}/run_summary.json",
        }
        global_rows.append(global_row)
        trial_summaries.append(global_row)

        trial_manifest["contract_addresses"] = {
            "ledger": summary["contract_address"],
            "verifier": ledger["verifier_contract_address"],
        }
        trial_manifest["environment"]["kubo_version"] = "0.29.0"
        trial_manifest["completion_status"] = "completed"
        trial_manifest["end_timestamp"] = utc_now()
        refresh_missing_fields(trial_manifest)
        validate_manifest(trial_manifest)
        write_json(trial_dir / "manifests" / "run_manifest.json", trial_manifest)
        trial_manifests.append(trial_manifest)

    comparison = baseline_comparison(config, node_rows, global_rows, gas_rows)
    reproduction = {
        "schema_version": "fairai.legacy_reproduction_summary.v1",
        "scenario_id": config["scenario_id"],
        "trials": trials,
        "all_baseline_values_matched": comparison["all_matched"],
        "mean_runtime_ms": mean([row["runtime_ms"] for row in global_rows]),
        "mean_proof_generation_ms": mean(
            [row["proof_generation_ms"] for row in proof_rows]
        ),
        "mean_ipfs_retrieval_ms": mean(
            [row["retrieval_ms"] for row in ipfs_rows if row["valid"]]
        ),
        "trial_summaries": trial_summaries,
    }
    write_json(output_dir / "reproduction_summary.json", reproduction)
    write_json(output_dir / "baseline_comparison.json", comparison)
    write_json(output_dir / "lifecycle.json", lifecycle)
    write_csv(output_dir / "node_metrics.csv", node_rows, list(node_rows[0]))
    write_csv(output_dir / "global_metrics.csv", global_rows, list(global_rows[0]))
    write_csv(output_dir / "gas.csv", gas_rows, list(gas_rows[0]))
    write_csv(
        output_dir / "artifact_inventory.csv", artifact_rows, list(artifact_rows[0])
    )
    write_csv(output_dir / "proof_timings.csv", proof_rows, list(proof_rows[0]))
    write_csv(output_dir / "ipfs_timings.csv", ipfs_rows, list(ipfs_rows[0]))

    return {
        "dataset_checksum": None,
        "partition_checksum": None,
        "summary": {
            "trials": trials,
            "all_baseline_values_matched": comparison["all_matched"],
            "mean_runtime_ms": reproduction["mean_runtime_ms"],
            "mean_proof_generation_ms": reproduction["mean_proof_generation_ms"],
            "mean_ipfs_retrieval_ms": reproduction["mean_ipfs_retrieval_ms"],
        },
        "manifest_updates": {
            "contract_addresses": trial_manifests[0]["contract_addresses"],
            "environment.kubo_version": "0.29.0",
        },
    }


def run_partition_analysis(config, output_dir):
    from .data import load_adult, load_compas
    from .partition import (
        export_partition_evidence,
        parse_partition_spec,
        partition_clients,
    )

    raw_root = REPO_ROOT / "data" / "raw"
    dataset_name = config["dataset"]
    if dataset_name == "adult":
        dataset_dir = raw_root / "adult"
        dataset = load_adult(dataset_dir, seed=config["seed"])
    elif dataset_name == "compas":
        dataset_dir = raw_root / "compas"
        dataset = load_compas(
            dataset_dir / "compas-scores-two-years.csv", seed=config["seed"]
        )
    else:
        raise ValueError(f"Unsupported partition-analysis dataset: {dataset_name}")

    download_manifest_path = dataset_dir / "download_manifest.json"
    if not download_manifest_path.is_file():
        raise FileNotFoundError(
            f"Dataset acquisition manifest is required: {download_manifest_path}"
        )
    download_manifest = json.loads(
        download_manifest_path.read_text(encoding="utf-8")
    )
    dataset_checksum = download_manifest["archive_sha256"]
    protected = dataset.train.protected[dataset.primary_protected_attribute].to_numpy()
    partition_specs = config.get("partitions", [])
    if not partition_specs:
        raise ValueError("partition_analysis requires at least one partition setting")

    partition_rows = []
    suite_checksums = {}
    output_files = (
        "entropy_by_client.csv",
        "entropy_summary.csv",
        "entropy_correlations.csv",
        "partition_summary.csv",
    )
    aggregate_rows = {filename: [] for filename in output_files}
    aggregate_fields = {}
    for partition_spec in partition_specs:
        mode, alpha = parse_partition_spec(partition_spec)
        result = partition_clients(
            dataset.train.labels,
            protected,
            client_count=config["clients"],
            mode=mode,
            seed=config["seed"],
            alpha=alpha,
            minimum_samples=config.get("minimum_samples_per_client", 50),
            max_attempts=config.get("partition_max_attempts", 1000),
        )
        partition_dir = output_dir / "partitions" / partition_spec
        evidence = export_partition_evidence(
            partition_dir, result, dataset.train.labels, protected
        )
        suite_checksums[partition_spec] = result.checksum
        partition_rows.append(
            {
                "partition": partition_spec,
                "mode": mode,
                "alpha": alpha,
                "checksum": result.checksum,
                "source_entropy": evidence["source_entropy"],
                "attempts": result.attempts,
            }
        )
        for filename in output_files:
            with (partition_dir / filename).open(encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                rows = [
                    {"partition": partition_spec, **row}
                    for row in reader
                ]
                aggregate_rows[filename].extend(rows)
                aggregate_fields[filename] = ["partition", *(reader.fieldnames or [])]

    for filename in output_files:
        write_csv(
            output_dir / "partitions" / filename,
            aggregate_rows[filename],
            aggregate_fields[filename],
        )
    partition_checksum = __import__("hashlib").sha256(
        canonical_json_bytes(suite_checksums)
    ).hexdigest()
    write_json(
        output_dir / "partitions" / "partition_checksums.json",
        {
            "schema_version": "fairai.partition_suite.v1",
            "dataset": dataset_name,
            "dataset_checksum": dataset_checksum,
            "suite_partition_checksum": partition_checksum,
            "partitions": suite_checksums,
        },
    )
    return {
        "dataset_checksum": dataset_checksum,
        "partition_checksum": partition_checksum,
        "summary": {
            "dataset": dataset_name,
            "training_samples": len(dataset.train.labels),
            "clients": config["clients"],
            "minimum_samples_per_client": config.get(
                "minimum_samples_per_client", 50
            ),
            "partitions": partition_rows,
            "correlation_status": (
                "undefined until local training and group-fairness outcomes are available"
            ),
        },
    }


def run_federated_core(config, output_dir):
    import numpy as np

    from .data import load_adult, load_compas
    from .federated import run_federated_method
    from .partition import (
        export_partition_evidence,
        parse_partition_spec,
        partition_clients,
    )
    from .policy import load_policy_profiles

    raw_root = REPO_ROOT / "data" / "raw"
    if config["dataset"] == "adult":
        dataset_dir = raw_root / "adult"
        dataset = load_adult(dataset_dir, seed=config["seed"])
    elif config["dataset"] == "compas":
        dataset_dir = raw_root / "compas"
        dataset = load_compas(
            dataset_dir / "compas-scores-two-years.csv", seed=config["seed"]
        )
    else:
        raise ValueError(f"Unsupported federated dataset: {config['dataset']}")
    download_manifest = json.loads(
        (dataset_dir / "download_manifest.json").read_text(encoding="utf-8")
    )
    profiles = load_policy_profiles(
        REPO_ROOT / "configs" / "revision" / "policy_profiles.json"
    )
    default_profile = config["fairness_policy"].removesuffix("_policy")
    profile_names = config.get("policy_profiles", [default_profile])
    try:
        selected_profiles = {
            profile_name: profiles[profile_name] for profile_name in profile_names
        }
    except KeyError as exc:
        raise ValueError(f"Unknown fairness policy: {exc.args[0]}") from exc
    methods = config.get("executable_methods", [])
    if not methods:
        raise ValueError("federated_core requires executable_methods")
    attack_profiles = config.get(
        "attack_profiles", [config.get("attack_profile", "none")]
    )
    executions = [
        (profile_name, policy, method, attack_type)
        for profile_name, policy in selected_profiles.items()
        for method in methods
        for attack_type in attack_profiles
    ]

    seeds = experiment_seeds(config)
    protected = dataset.train.protected[
        dataset.primary_protected_attribute
    ].to_numpy()
    partition_checksums = {}
    global_rows = []
    client_rows = []
    test_rows = []
    method_summaries = []
    client_counts = config.get("client_counts", [config["clients"]])
    if not client_counts or not all(
        isinstance(client_count, int) and client_count > 1
        for client_count in client_counts
    ):
        raise ValueError("client_counts must contain integers greater than one")
    if len(set(client_counts)) != len(client_counts):
        raise ValueError("client_counts must be unique")
    for experiment_seed in seeds:
        for client_count in client_counts:
            for partition_spec in config.get("partitions", ["iid"]):
                mode, alpha = parse_partition_spec(partition_spec)
                partition = partition_clients(
                    dataset.train.labels,
                    protected,
                    client_count=client_count,
                    mode=mode,
                    seed=experiment_seed,
                    alpha=alpha,
                    minimum_samples=config.get("minimum_samples_per_client", 50),
                )
                partition_key = (
                    f"seed_{experiment_seed}/clients_{client_count}/{partition_spec}"
                )
                partition_checksums[partition_key] = partition.checksum
                export_partition_evidence(
                    output_dir
                    / "partitions"
                    / f"seed_{experiment_seed}"
                    / f"clients_{client_count}"
                    / partition_spec,
                    partition,
                    dataset.train.labels,
                    protected,
                )
                for profile_name, policy, method, attack_type in executions:
                    result = run_federated_method(
                        dataset=dataset,
                        partition=partition,
                        method=method,
                        policy=policy,
                        model_type=config["model"],
                        rounds=config["rounds"],
                        local_epochs=config["local_epochs"],
                        seed=experiment_seed,
                        minimum_group_samples=config.get(
                            "minimum_group_samples", 10
                        ),
                        attack_type=attack_type,
                        malicious_client_ratio=config.get(
                            "malicious_client_ratio", 0.0
                        ),
                    )
                    dimensions = {
                        "scenario_id": config["scenario_id"],
                        "seed": experiment_seed,
                        "client_count": client_count,
                        "partition": partition_spec,
                        "policy_profile": profile_name,
                        "attack_type": attack_type,
                    }
                    global_rows.extend(
                        {**dimensions, **row} for row in result["round_metrics"]
                    )
                    client_rows.extend(
                        {**dimensions, **row} for row in result["client_metrics"]
                    )
                    test_metrics = result["test_metrics"]
                    test_rows.append(
                        {
                            **dimensions,
                            "method": method,
                            "accuracy": test_metrics["accuracy"],
                            "macro_f1": test_metrics["macro_f1"],
                            "demographic_parity_gap": test_metrics[
                                "demographic_parity_gap"
                            ],
                            "equal_opportunity_gap": test_metrics[
                                "equal_opportunity_gap"
                            ],
                            "equalized_odds_gap": test_metrics[
                                "equalized_odds_gap"
                            ],
                            "subgroup_accuracy_gap": test_metrics[
                                "subgroup_accuracy_gap"
                            ],
                            "runtime_ms": result["runtime_ms"],
                        }
                    )
                    model_path = (
                        output_dir
                        / "models"
                        / (
                            f"seed_{experiment_seed}-clients_{client_count}-"
                            f"{partition_spec}-{profile_name}-{attack_type}-"
                            f"{method}-"
                            "final_parameters.npz"
                        )
                    )
                    np.savez_compressed(
                        model_path,
                        **{
                            f"parameter_{index}": value
                            for index, value in enumerate(
                                result["final_parameters"]
                            )
                        },
                    )
                    method_summaries.append(
                        {
                            "seed": experiment_seed,
                            "client_count": client_count,
                            "partition": partition_spec,
                            "policy_profile": profile_name,
                            "attack_type": attack_type,
                            "method": method,
                            "runtime_ms": result["runtime_ms"],
                            "final_validation_accuracy": result[
                                "round_metrics"
                            ][-1]["global_accuracy"],
                            "test_accuracy": test_metrics["accuracy"],
                        }
                    )
    write_csv(
        output_dir / "metrics" / "fairness_metrics_by_client.csv",
        client_rows,
        list(client_rows[0]),
    )
    write_csv(
        output_dir / "metrics" / "fairness_metrics_global.csv",
        global_rows,
        list(global_rows[0]),
    )
    write_csv(
        output_dir / "metrics" / "test_metrics.csv",
        test_rows,
        list(test_rows[0]),
    )
    partition_checksum = __import__("hashlib").sha256(
        canonical_json_bytes(partition_checksums)
    ).hexdigest()
    return {
        "dataset_checksum": download_manifest["archive_sha256"],
        "partition_checksum": partition_checksum,
        "summary": {
            "dataset": config["dataset"],
            "split_seed": config["seed"],
            "experiment_seeds": seeds,
            "client_counts": client_counts,
            "methods_executed": methods,
            "policy_profiles": profile_names,
            "attack_profiles": attack_profiles,
            "methods_not_executed": config.get("methods_not_executed", {}),
            "partitions": partition_checksums,
            "results": method_summaries,
            "test_set_usage": "evaluated once after final round for each paired method",
        },
    }


EXECUTORS = {
    "smoke": run_smoke,
    "legacy_mvp": run_legacy,
    "partition_analysis": run_partition_analysis,
    "federated_core": run_federated_core,
}


def execute(config_path, output_root, run_id=None, parent_suite_id=None, resume=False):
    config = load_config(config_path)
    run_id = run_id or f"{config['scenario_id']}-{config_hash(config)[:12]}"
    output_dir = Path(output_root) / run_id
    manifest_path = output_dir / "manifests" / "run_manifest.json"

    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        same_config = existing.get("configuration_hash") == config_hash(config)
        if resume and same_config and existing.get("completion_status") == "completed":
            return output_dir, existing
        if not resume:
            raise FileExistsError(
                f"Run directory already exists: {output_dir}. Use --resume or a new --run-id."
            )
        if not same_config:
            raise ValueError("Cannot resume with a different configuration")

    output_dir = prepare_output(output_dir)
    write_json(output_dir / "config" / "resolved_config.json", config)
    manifest = new_manifest(config, run_id, parent_suite_id, REPO_ROOT)
    validate_manifest(manifest)
    write_json(manifest_path, manifest)

    try:
        executor = EXECUTORS.get(config["executor"])
        if executor is None:
            raise NotImplementedError(
                f"Executor '{config['executor']}' is planned but not implemented"
            )
        result = executor(config, output_dir)
        manifest["dataset_checksum"] = result["dataset_checksum"]
        manifest["partition_checksum"] = result["partition_checksum"]
        updates = result.get("manifest_updates", {})
        if "contract_addresses" in updates:
            manifest["contract_addresses"] = updates["contract_addresses"]
        if "environment.kubo_version" in updates:
            manifest["environment"]["kubo_version"] = updates["environment.kubo_version"]
        write_json(output_dir / "derived" / "summary.json", result["summary"])
        manifest["completion_status"] = "completed"
    except Exception as exc:
        manifest["completion_status"] = "failed"
        manifest["errors"].append(
            {
                "type": type(exc).__name__,
                "message": str(exc),
            }
        )
        (output_dir / "logs" / "failure.log").write_text(
            traceback.format_exc(), encoding="utf-8"
        )
        raise
    finally:
        manifest["end_timestamp"] = utc_now()
        refresh_missing_fields(manifest)
        validate_manifest(manifest)
        write_json(manifest_path, manifest)
    return output_dir, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a FairAI major-revision scenario")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--run-id")
    parser.add_argument("--parent-suite-id")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    output_dir, manifest = execute(
        args.config,
        args.output_root,
        run_id=args.run_id,
        parent_suite_id=args.parent_suite_id,
        resume=args.resume,
    )
    print(
        json.dumps(
            {
                "run_id": manifest["run_id"],
                "status": manifest["completion_status"],
                "output_dir": str(output_dir.relative_to(REPO_ROOT)),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
