import argparse
import csv
import json
import sys
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


def run_legacy(config, output_dir):
    from scripts.fairai_mvp import run_pipeline

    summary = run_pipeline(
        output_dir / "raw" / "legacy_run",
        force_zk=config.get("force_zk", False),
        require_real_ipfs=config.get("require_real_ipfs", True),
    )
    return {
        "dataset_checksum": None,
        "partition_checksum": None,
        "summary": {
            "approved_nodes": summary["approved_nodes"],
            "rejected_nodes": summary["rejected_nodes"],
            "global_accuracy": summary["global_model"]["validation_metrics"]["accuracy"],
            "global_demographic_parity_gap": summary["global_model"]["validation_metrics"][
                "demographic_parity_gap"
            ],
        },
    }


EXECUTORS = {
    "smoke": run_smoke,
    "legacy_mvp": run_legacy,
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
