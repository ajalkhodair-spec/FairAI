import hashlib
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import config_hash


OUTPUT_DIRS = (
    "config",
    "environment",
    "raw",
    "derived",
    "logs",
    "datasets",
    "partitions",
    "models",
    "metrics",
    "proofs",
    "ipfs",
    "blockchain",
    "attacks",
    "statistics",
    "reports",
    "manifests",
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    path = Path(path)
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command_output(args, cwd):
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip().splitlines()[0] if result.stdout.strip() else None


def git_state(root):
    commit = command_output(["git", "rev-parse", "HEAD"], root)
    status = command_output(["git", "status", "--porcelain"], root)
    return {
        "commit": commit,
        "dirty": bool(status),
    }


def prepare_output(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for name in OUTPUT_DIRS:
        (root / name).mkdir(exist_ok=True)
    return root


def environment_snapshot(repo_root):
    repo_root = Path(repo_root)
    hardhat_version = command_output(
        ["npx", "hardhat", "--version"], repo_root / "hardhat"
    )
    return {
        "operating_system": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "cpu_count": os.cpu_count(),
        "memory_bytes": None,
        "python_version": platform.python_version(),
        "node_version": command_output(["node", "--version"], repo_root),
        "hardhat_version": hardhat_version,
        "solidity_compiler_version": "0.8.20",
        "kubo_version": None,
        "docker_version": command_output(["docker", "--version"], repo_root),
        "snarkjs_version": "0.7.5" if shutil.which("snarkjs") else None,
        "circom_version": command_output(["circom", "--version"], repo_root),
        "package_lock_hash": sha256_file(repo_root / "hardhat" / "package-lock.json"),
    }


def refresh_missing_fields(manifest):
    missing = []
    top_level_fields = (
        "git_commit",
        "dataset_checksum",
        "partition_checksum",
        "circuit_hash",
        "proving_key_hash",
        "verification_key_hash",
    )
    for field in top_level_fields:
        if manifest.get(field) is None:
            missing.append(field)
    for field, value in manifest.get("environment", {}).items():
        if value is None:
            missing.append(f"environment.{field}")
    if not manifest.get("contract_addresses"):
        missing.append("contract_addresses")
    if not manifest.get("contract_bytecode_hashes"):
        missing.append("contract_bytecode_hashes")
    manifest["missing_fields"] = sorted(missing)
    return manifest


def new_manifest(config, run_id, parent_suite_id, repo_root):
    git = git_state(repo_root)
    env = environment_snapshot(repo_root)
    manifest = {
        "schema_version": "fairai.revision.run_manifest.v1",
        "run_id": run_id,
        "parent_suite_id": parent_suite_id,
        "scenario_id": config["scenario_id"],
        "evidence_type": config["evidence_type"],
        "git_commit": git["commit"],
        "dirty_tree": git["dirty"],
        "configuration_hash": config_hash(config),
        "seed": config["seed"],
        "dataset": config["dataset"],
        "dataset_checksum": None,
        "partition_checksum": None,
        "model": config["model"],
        "client_count": config["clients"],
        "rounds": config["rounds"],
        "local_epochs": config["local_epochs"],
        "method": config["method"],
        "fairness_policy": config["fairness_policy"],
        "attack_profile": config["attack_profile"],
        "start_timestamp": utc_now(),
        "end_timestamp": None,
        "environment": env,
        "contract_addresses": {},
        "contract_bytecode_hashes": {},
        "circuit_hash": sha256_file(Path(repo_root) / "circuits" / "FairnessEligibility.circom"),
        "proving_key_hash": sha256_file(Path(repo_root) / "build" / "FairnessEligibility_final.zkey"),
        "verification_key_hash": sha256_file(Path(repo_root) / "build" / "FairnessEligibility_vkey.json"),
        "completion_status": "running",
        "missing_fields": [],
        "errors": [],
    }
    return refresh_missing_fields(manifest)


def validate_manifest(payload):
    required = {
        "schema_version",
        "run_id",
        "scenario_id",
        "configuration_hash",
        "seed",
        "environment",
        "completion_status",
        "missing_fields",
        "errors",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"Manifest missing fields: {missing}")
    if payload["schema_version"] != "fairai.revision.run_manifest.v1":
        raise ValueError("Unsupported manifest schema")
    if payload["completion_status"] not in {"running", "completed", "failed", "partial"}:
        raise ValueError("Invalid completion_status")


def write_json(path, payload):
    path = Path(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
