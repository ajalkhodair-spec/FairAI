import json
from pathlib import Path


POLICY_METRICS = {
    "accuracy": ("minimum_accuracy", "minimum"),
    "demographic_parity_gap": ("maximum_demographic_parity_gap", "maximum"),
    "equal_opportunity_gap": ("maximum_equal_opportunity_gap", "maximum"),
    "equalized_odds_gap": ("maximum_equalized_odds_gap", "maximum"),
    "subgroup_accuracy_gap": ("maximum_subgroup_accuracy_gap", "maximum"),
}
UNDEFINED_BEHAVIORS = {"reject", "ignore", "error"}


class PolicyError(ValueError):
    pass


def load_policy_profiles(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != "fairai.policy_profiles.v1":
        raise PolicyError("Unsupported policy profile collection")
    profiles = {}
    for policy in payload.get("profiles", []):
        validate_policy(policy)
        name = policy["name"]
        if name in profiles:
            raise PolicyError(f"Duplicate policy profile: {name}")
        profiles[name] = policy
    if not profiles:
        raise PolicyError("At least one policy profile is required")
    return profiles


def validate_policy(policy):
    required = {
        "policy_version",
        "name",
        "minimum_accuracy",
        "maximum_demographic_parity_gap",
        "maximum_equal_opportunity_gap",
        "maximum_equalized_odds_gap",
        "maximum_subgroup_accuracy_gap",
        "enabled_metrics",
        "semantics",
        "undefined_metric_behavior",
        "valid_round_start",
        "valid_round_end",
    }
    missing = sorted(required - set(policy))
    if missing:
        raise PolicyError(f"Policy missing fields: {missing}")
    if policy["semantics"] != "AND":
        raise PolicyError("Only explicit AND policy semantics are supported")
    if policy["undefined_metric_behavior"] not in UNDEFINED_BEHAVIORS:
        raise PolicyError("Unsupported undefined_metric_behavior")
    if policy["valid_round_start"] < 0:
        raise PolicyError("valid_round_start must be nonnegative")
    if policy["valid_round_end"] < policy["valid_round_start"]:
        raise PolicyError("valid_round_end precedes valid_round_start")
    enabled = policy["enabled_metrics"]
    if set(enabled) != set(POLICY_METRICS):
        raise PolicyError("enabled_metrics must define the complete metric mask")
    if not all(isinstance(value, bool) for value in enabled.values()):
        raise PolicyError("enabled_metrics values must be boolean")
    if not any(enabled.values()):
        raise PolicyError("At least one policy metric must be enabled")
    for metric, (threshold_field, _) in POLICY_METRICS.items():
        threshold = policy[threshold_field]
        if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
            raise PolicyError(f"{threshold_field} must be between zero and one")


def evaluate_policy(metrics, policy, round_id):
    validate_policy(policy)
    if not policy["valid_round_start"] <= round_id <= policy["valid_round_end"]:
        return {
            "schema_version": "fairai.policy_decision.v1",
            "policy_version": policy["policy_version"],
            "policy_name": policy["name"],
            "round_id": round_id,
            "approved": False,
            "checks": [],
            "reasons": ["policy is not valid for this round"],
        }

    checks = []
    reasons = []
    for metric, (threshold_field, comparison) in POLICY_METRICS.items():
        if not policy["enabled_metrics"][metric]:
            continue
        value = metrics.get(metric)
        threshold = policy[threshold_field]
        if value is None:
            behavior = policy["undefined_metric_behavior"]
            if behavior == "error":
                raise PolicyError(f"Enabled metric is undefined: {metric}")
            passed = behavior == "ignore"
            reason = f"{metric} is undefined; policy behavior is {behavior}"
        elif comparison == "minimum":
            passed = value >= threshold
            reason = (
                f"{metric}={value:.12g} must be at least {threshold:.12g}"
            )
        else:
            passed = value <= threshold
            reason = (
                f"{metric}={value:.12g} must be at most {threshold:.12g}"
            )
        checks.append(
            {
                "metric": metric,
                "value": value,
                "threshold": threshold,
                "comparison": comparison,
                "passed": passed,
                "reason": reason,
            }
        )
        if not passed:
            reasons.append(reason)

    return {
        "schema_version": "fairai.policy_decision.v1",
        "policy_version": policy["policy_version"],
        "policy_name": policy["name"],
        "round_id": round_id,
        "approved": not reasons,
        "checks": checks,
        "reasons": reasons,
    }
