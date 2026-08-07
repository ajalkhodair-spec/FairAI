from dataclasses import dataclass

import numpy as np


class AggregationError(ValueError):
    pass


@dataclass(frozen=True)
class ClientUpdate:
    client_id: str
    parameters: tuple
    sample_count: int
    valid: bool = True
    policy_approved: bool | None = None
    proof_verified: bool | None = None
    artifact_binding_valid: bool | None = None
    decision_signed: bool | None = None
    on_chain_approved: bool | None = None


@dataclass(frozen=True)
class BaselineSpec:
    method: str
    aggregation: str
    eligibility: str
    blockchain: bool
    ipfs: bool
    fairness_assessment: str
    groth16: bool
    signed_verifier: bool


BASELINE_SPECS = {
    "B0": BaselineSpec("B0", "fedavg", "valid", False, False, "none", False, False),
    "B1": BaselineSpec(
        "B1", "fedavg", "valid", False, False, "post_hoc", False, False
    ),
    "B2": BaselineSpec(
        "B2", "fedavg", "valid", True, True, "post_hoc", False, False
    ),
    "B3": BaselineSpec(
        "B3", "fedavg", "policy", True, True, "pre_aggregation", False, False
    ),
    "B4": BaselineSpec(
        "B4", "fedavg", "full_fairai", True, True, "pre_aggregation", True, True
    ),
    "B5": BaselineSpec(
        "B5", "fairfed", "valid", False, False, "fairness_aware", False, False
    ),
    "B6": BaselineSpec(
        "B6", "coordinate_median", "valid", False, False, "none", False, False
    ),
    "B7": BaselineSpec(
        "B7",
        "coordinate_median",
        "full_fairai",
        True,
        True,
        "pre_aggregation",
        True,
        True,
    ),
}


def _validate_updates(updates):
    updates = list(updates)
    if not updates:
        raise AggregationError("At least one client update is required")
    reference_shapes = tuple(np.asarray(value).shape for value in updates[0].parameters)
    if not reference_shapes:
        raise AggregationError("Client parameters must not be empty")
    for update in updates:
        if update.sample_count < 1:
            raise AggregationError("sample_count must be positive")
        if len(update.parameters) != len(reference_shapes):
            raise AggregationError("Client parameter lists have different lengths")
        shapes = tuple(np.asarray(value).shape for value in update.parameters)
        if shapes != reference_shapes:
            raise AggregationError("Client parameter shapes do not match")
        if not all(np.isfinite(np.asarray(value, dtype=float)).all() for value in update.parameters):
            raise AggregationError("Client parameters must be finite")
    return updates


def fedavg(updates):
    updates = _validate_updates(updates)
    weights = np.asarray([update.sample_count for update in updates], dtype=float)
    weights /= weights.sum()
    return tuple(
        np.sum(
            np.stack(
                [np.asarray(update.parameters[index], dtype=float) for update in updates]
            )
            * weights.reshape((-1,) + (1,) * len(np.asarray(updates[0].parameters[index]).shape)),
            axis=0,
        )
        for index in range(len(updates[0].parameters))
    )


def weighted_average(updates, weights):
    updates = _validate_updates(updates)
    try:
        values = np.asarray([weights[update.client_id] for update in updates], dtype=float)
    except KeyError as exc:
        raise AggregationError(f"Missing aggregation weight for client {exc.args[0]}") from exc
    if not np.isfinite(values).all():
        raise AggregationError("Aggregation weights must be finite")
    if not np.isclose(values.sum(), 1.0, atol=1e-10):
        raise AggregationError("Aggregation weights must sum to one")
    return tuple(
        np.sum(
            np.stack(
                [np.asarray(update.parameters[index], dtype=float) for update in updates]
            )
            * values.reshape(
                (-1,) + (1,) * len(np.asarray(updates[0].parameters[index]).shape)
            ),
            axis=0,
        )
        for index in range(len(updates[0].parameters))
    )


def _aggregate_rate(metrics, group, rate):
    numerator = 0
    denominator = 0
    for client_metrics in metrics.values():
        group_metrics = client_metrics.get("groups", {}).get(group)
        if group_metrics is None:
            continue
        value = group_metrics[rate]
        numerator += int(value["numerator"])
        denominator += int(value["denominator"])
    return None if denominator == 0 else numerator / denominator


def fairfed_weights(
    updates,
    client_metrics,
    beta=1.0,
    previous_raw_weights=None,
):
    """Apply the FairFed server weighting rule from Ezzeldin et al. (2023)."""
    updates = _validate_updates(updates)
    if not np.isfinite(beta) or beta < 0:
        raise AggregationError("FairFed beta must be finite and non-negative")
    client_ids = [update.client_id for update in updates]
    missing = set(client_ids) - set(client_metrics)
    if missing:
        raise AggregationError(
            "Missing FairFed evaluation metrics for clients: " + ",".join(sorted(missing))
        )

    first = client_metrics[client_ids[0]]
    privileged = str(first["privileged_value"])
    unprivileged = str(first["unprivileged_value"])
    privileged_tpr = _aggregate_rate(client_metrics, privileged, "true_positive_rate")
    unprivileged_tpr = _aggregate_rate(client_metrics, unprivileged, "true_positive_rate")
    global_eod = (
        None
        if privileged_tpr is None or unprivileged_tpr is None
        else float(unprivileged_tpr - privileged_tpr)
    )
    correct = sum(
        int(group["accuracy"]["numerator"])
        for metrics in client_metrics.values()
        for group in metrics["groups"].values()
    )
    count = sum(
        int(group["accuracy"]["denominator"])
        for metrics in client_metrics.values()
        for group in metrics["groups"].values()
    )
    if count == 0:
        raise AggregationError("FairFed global accuracy is undefined")
    global_accuracy = correct / count

    deltas = {}
    metric_sources = {}
    for client_id in client_ids:
        metrics = client_metrics[client_id]
        local_eod = metrics.get("equal_opportunity_difference")
        if global_eod is not None and local_eod is not None:
            deltas[client_id] = abs(global_eod - float(local_eod))
            metric_sources[client_id] = "equal_opportunity_difference"
        else:
            deltas[client_id] = abs(global_accuracy - float(metrics["accuracy"]))
            metric_sources[client_id] = "accuracy_fallback"

    if previous_raw_weights is None:
        total_samples = sum(update.sample_count for update in updates)
        previous = {
            update.client_id: update.sample_count / total_samples for update in updates
        }
    else:
        missing = set(client_ids) - set(previous_raw_weights)
        if missing:
            raise AggregationError(
                "Missing previous FairFed weights for clients: "
                + ",".join(sorted(missing))
            )
        previous = {
            client_id: float(previous_raw_weights[client_id]) for client_id in client_ids
        }
        if not np.isfinite(list(previous.values())).all():
            raise AggregationError("Previous FairFed weights must be finite")

    mean_delta = float(np.mean(list(deltas.values())))
    raw_weights = {
        client_id: previous[client_id] - beta * (deltas[client_id] - mean_delta)
        for client_id in client_ids
    }
    normalizer = sum(raw_weights.values())
    if not np.isfinite(normalizer) or np.isclose(normalizer, 0.0):
        raise AggregationError("FairFed weights cannot be normalized")
    normalized_weights = {
        client_id: value / normalizer for client_id, value in raw_weights.items()
    }
    return {
        "weights": normalized_weights,
        "raw_weights": raw_weights,
        "deltas": deltas,
        "metric_sources": metric_sources,
        "global_equal_opportunity_difference": global_eod,
        "global_accuracy": global_accuracy,
        "mean_delta": mean_delta,
        "beta": float(beta),
    }


def coordinate_median(updates):
    updates = _validate_updates(updates)
    return tuple(
        np.median(
            np.stack(
                [np.asarray(update.parameters[index], dtype=float) for update in updates]
            ),
            axis=0,
        )
        for index in range(len(updates[0].parameters))
    )


def eligible_updates(method, updates):
    try:
        spec = BASELINE_SPECS[method]
    except KeyError as exc:
        raise AggregationError(f"Unsupported baseline method: {method}") from exc
    selected = []
    exclusions = {}
    for update in updates:
        reason = None
        if not update.valid:
            reason = "invalid_update"
        elif spec.eligibility == "policy" and update.policy_approved is not True:
            reason = "policy_not_approved"
        elif spec.eligibility == "full_fairai":
            required = {
                "policy_approved": update.policy_approved,
                "proof_verified": update.proof_verified,
                "artifact_binding_valid": update.artifact_binding_valid,
                "decision_signed": update.decision_signed,
                "on_chain_approved": update.on_chain_approved,
            }
            failed = [name for name, value in required.items() if value is not True]
            if failed:
                reason = "full_fairai_checks_failed:" + ",".join(failed)
        if reason is None:
            selected.append(update)
        else:
            exclusions[update.client_id] = reason
    if not selected:
        raise AggregationError("Eligibility filtering produced an empty update set")
    return selected, exclusions


def aggregate_for_method(method, updates, aggregation_weights=None):
    selected, exclusions = eligible_updates(method, updates)
    spec = BASELINE_SPECS[method]
    if spec.aggregation == "fedavg":
        parameters = fedavg(selected)
    elif spec.aggregation == "coordinate_median":
        parameters = coordinate_median(selected)
    elif spec.aggregation == "fairfed":
        if aggregation_weights is None:
            raise AggregationError("B5 requires explicit FairFed aggregation weights")
        parameters = weighted_average(selected, aggregation_weights)
    else:
        raise AggregationError(f"Unsupported aggregation: {spec.aggregation}")
    return {
        "method": method,
        "specification": spec,
        "parameters": parameters,
        "included_clients": [update.client_id for update in selected],
        "excluded_clients": exclusions,
    }
