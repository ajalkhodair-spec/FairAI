import hashlib
import json
import math

from .policy import evaluate_policy


BN254_SCALAR_FIELD = (
    21888242871839275222246405745257275088548364400416034343698204186575808495617
)


class BindingError(ValueError):
    pass


def policy_version_to_uint64(version):
    try:
        parts = [int(part) for part in str(version).split(".")]
    except ValueError as exc:
        raise BindingError("policy_version must use MAJOR.MINOR.PATCH integers") from exc
    if len(parts) != 3 or any(part < 0 or part > 65535 for part in parts):
        raise BindingError("policy_version components must be uint16 values")
    major, minor, patch = parts
    return (major << 32) | (minor << 16) | patch


def _validate_canonical_value(value, path="$"):
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise BindingError(f"Non-finite number at {path}")
        raise BindingError(
            f"Floating-point value at {path}; use scaled integers or decimal strings"
        )
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_canonical_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise BindingError(f"Object keys must be strings at {path}")
        for key, item in value.items():
            _validate_canonical_value(item, f"{path}.{key}")
        return
    raise BindingError(f"Unsupported canonical JSON type at {path}: {type(value).__name__}")


def canonical_artifact_bytes(payload):
    _validate_canonical_value(payload)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_digest(payload):
    return hashlib.sha256(canonical_artifact_bytes(payload)).hexdigest()


def digest_to_bn254_field(digest):
    if not isinstance(digest, str) or len(digest) != 64:
        raise BindingError("SHA-256 digest must be a 64-character hexadecimal string")
    try:
        value = int(digest, 16)
    except ValueError as exc:
        raise BindingError("SHA-256 digest is not hexadecimal") from exc
    return value % BN254_SCALAR_FIELD


def artifact_binding_fields(manifest, metrics):
    manifest_digest = sha256_digest(manifest)
    metrics_digest = sha256_digest(metrics)
    return {
        "manifest_digest": manifest_digest,
        "manifest_digest_field": digest_to_bn254_field(manifest_digest),
        "metrics_digest": metrics_digest,
        "metrics_digest_field": digest_to_bn254_field(metrics_digest),
    }


def verify_v2_binding(
    manifest,
    metrics,
    public_inputs,
    policy,
    groth16_verified,
):
    binding = artifact_binding_fields(manifest, metrics)
    scale = metrics.get("scale")
    if not isinstance(scale, int) or scale <= 0:
        raise BindingError("metrics scale must be a positive integer")
    metric_inputs = {
        "accuracy": "accuracy",
        "demographic_parity_gap": "demographic_parity_gap",
        "equal_opportunity_gap": "equal_opportunity_gap",
        "equalized_odds_gap": "equalized_odds_gap",
        "subgroup_accuracy_gap": "subgroup_accuracy_gap",
    }
    threshold_inputs = {
        "minimum_accuracy": "minimum_accuracy",
        "maximum_demographic_parity_gap": "maximum_demographic_parity_gap",
        "maximum_equal_opportunity_gap": "maximum_equal_opportunity_gap",
        "maximum_equalized_odds_gap": "maximum_equalized_odds_gap",
        "maximum_subgroup_accuracy_gap": "maximum_subgroup_accuracy_gap",
    }
    enabled_inputs = {
        "enable_accuracy": "accuracy",
        "enable_demographic_parity": "demographic_parity_gap",
        "enable_equal_opportunity": "equal_opportunity_gap",
        "enable_equalized_odds": "equalized_odds_gap",
        "enable_subgroup_accuracy": "subgroup_accuracy_gap",
    }
    checks = {
        "manifest_digest_field": (
            int(public_inputs["manifest_digest_field"])
            == binding["manifest_digest_field"]
        ),
        "metrics_digest_field": (
            int(public_inputs["metrics_digest_field"]) == binding["metrics_digest_field"]
        ),
        "node_id": int(public_inputs["node_id"]) == int(manifest["node_id"]),
        "round_id": int(public_inputs["round_id"]) == int(manifest["round_id"]),
        "policy_version": int(public_inputs["policy_version"])
        == policy_version_to_uint64(manifest["policy_version"])
        == policy_version_to_uint64(policy["policy_version"]),
        "nonce": int(public_inputs["nonce"]) == int(manifest["nonce"]),
    }
    for input_name, metric_name in metric_inputs.items():
        value = metrics.get(metric_name)
        expected = 0 if value is None else int(value)
        checks[input_name] = int(public_inputs[input_name]) == expected
    for input_name, policy_name in threshold_inputs.items():
        expected = round(float(policy[policy_name]) * scale)
        checks[input_name] = int(public_inputs[input_name]) == expected
    for input_name, metric_name in enabled_inputs.items():
        expected = int(policy["enabled_metrics"][metric_name])
        checks[input_name] = int(public_inputs[input_name]) == expected
    artifact_binding_valid = all(checks.values())
    policy_metrics = {}
    for metric in (
        "accuracy",
        "demographic_parity_gap",
        "equal_opportunity_gap",
        "equalized_odds_gap",
        "subgroup_accuracy_gap",
    ):
        value = metrics.get(metric)
        policy_metrics[metric] = None if value is None else int(value) / scale
    policy_decision = evaluate_policy(
        policy_metrics, policy, round_id=int(manifest["round_id"])
    )
    return {
        "schema_version": "fairai.verifier_binding.v2",
        "proof_generated": bool(public_inputs.get("proof_generated", True)),
        "proof_verified": bool(groth16_verified),
        "artifact_binding_valid": artifact_binding_valid,
        "policy_passed": policy_decision["approved"],
        "decision_signed": False,
        "binding_checks": checks,
        "computed_binding": binding,
        "policy_decision": policy_decision,
    }
