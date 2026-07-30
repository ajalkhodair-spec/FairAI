import hashlib
import json
from pathlib import Path


REQUIRED_KEYS = {
    "schema_version",
    "scenario_id",
    "executor",
    "evidence_type",
    "seed",
    "dataset",
    "model",
    "clients",
    "rounds",
    "local_epochs",
    "method",
    "fairness_policy",
    "attack_profile",
}


class ConfigError(ValueError):
    pass


def canonical_json_bytes(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def config_hash(payload):
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def load_config(path):
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"{path} must use JSON-compatible YAML for the dependency-free runner: {exc}"
        ) from exc
    validate_config(payload)
    return payload


def validate_config(payload):
    if not isinstance(payload, dict):
        raise ConfigError("Configuration must be an object")
    missing = sorted(REQUIRED_KEYS - payload.keys())
    if missing:
        raise ConfigError(f"Missing required configuration fields: {missing}")
    if payload["schema_version"] != "fairai.revision.config.v1":
        raise ConfigError("Unsupported configuration schema_version")
    if not isinstance(payload["seed"], int):
        raise ConfigError("seed must be an integer")
    if not isinstance(payload["clients"], int) or payload["clients"] < 1:
        raise ConfigError("clients must be a positive integer")
    if not isinstance(payload["rounds"], int) or payload["rounds"] < 1:
        raise ConfigError("rounds must be a positive integer")
    if not isinstance(payload["local_epochs"], int) or payload["local_epochs"] < 1:
        raise ConfigError("local_epochs must be a positive integer")
    if payload["evidence_type"] not in {"measured", "derived", "modeled", "estimated"}:
        raise ConfigError("Unsupported evidence_type")

