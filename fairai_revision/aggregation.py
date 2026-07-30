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
    if method == "B5":
        raise AggregationError(
            "B5 FairFed is unavailable until the primary-paper weighting is "
            "implemented and independently verified"
        )
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


def aggregate_for_method(method, updates):
    selected, exclusions = eligible_updates(method, updates)
    spec = BASELINE_SPECS[method]
    if spec.aggregation == "fedavg":
        parameters = fedavg(selected)
    elif spec.aggregation == "coordinate_median":
        parameters = coordinate_median(selected)
    else:
        raise AggregationError(f"Unsupported aggregation: {spec.aggregation}")
    return {
        "method": method,
        "specification": spec,
        "parameters": parameters,
        "included_clients": [update.client_id for update in selected],
        "excluded_clients": exclusions,
    }
