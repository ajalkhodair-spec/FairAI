import copy
import time
from dataclasses import dataclass, replace

import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split

from .aggregation import (
    AggregationError,
    ClientUpdate,
    aggregate_for_method,
    eligible_updates,
    fairfed_weights,
)
from .data import TabularPreprocessor
from .fairness import evaluate_group_fairness
from .models import create_model
from .policy import evaluate_policy


class FederatedExperimentError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreparedData:
    train_features: np.ndarray
    train_labels: np.ndarray
    train_protected: np.ndarray
    validation_features: np.ndarray
    validation_labels: np.ndarray
    validation_protected: np.ndarray
    test_features: np.ndarray
    test_labels: np.ndarray
    test_protected: np.ndarray


def prepare_federated_data(dataset):
    preprocessor = TabularPreprocessor()
    train_features = preprocessor.fit(dataset.train.features)
    return PreparedData(
        train_features=train_features,
        train_labels=dataset.train.labels,
        train_protected=dataset.train.protected[
            dataset.primary_protected_attribute
        ].to_numpy(),
        validation_features=preprocessor.transform(dataset.validation.features),
        validation_labels=dataset.validation.labels,
        validation_protected=dataset.validation.protected[
            dataset.primary_protected_attribute
        ].to_numpy(),
        test_features=preprocessor.transform(dataset.test.features),
        test_labels=dataset.test.labels,
        test_protected=dataset.test.protected[
            dataset.primary_protected_attribute
        ].to_numpy(),
    )


def _local_train_evaluation_split(indices, labels, protected, seed):
    indices = np.asarray(indices, dtype=int)
    if len(indices) < 4:
        raise FederatedExperimentError("Client needs at least four samples")
    strata = np.asarray(
        [f"{labels[index]}|{protected[index]}" for index in indices]
    )
    unique, counts = np.unique(strata, return_counts=True)
    stratify = strata if len(unique) > 1 and counts.min() >= 2 else None
    train, evaluation = train_test_split(
        indices,
        test_size=0.2,
        random_state=seed,
        stratify=stratify,
    )
    return np.sort(train), np.sort(evaluation)


def _model_metrics(
    model,
    features,
    labels,
    protected,
    dataset,
    minimum_group_samples,
    timing_sink=None,
):
    started = time.perf_counter()
    predictions = model.predict(features)
    macro_f1 = float(f1_score(labels, predictions, average="macro"))
    evaluation_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    result = evaluate_group_fairness(
        labels,
        predictions,
        protected,
        privileged_value=dataset.privileged_value,
        unprivileged_value=dataset.unprivileged_value,
        favorable_label=dataset.favorable_label,
        minimum_group_samples=minimum_group_samples,
    )
    fairness_ms = (time.perf_counter() - started) * 1000
    result["macro_f1"] = macro_f1
    if timing_sink is not None:
        timing_sink["local_evaluation_ms"] = evaluation_ms
        timing_sink["fairness_computation_ms"] = fairness_ms
    return result


def _new_model(model_type, seed, local_epochs, input_dim, parameters=None):
    kwargs = {"seed": seed}
    if model_type == "logistic_regression":
        model_type = "federated_logistic_regression"
        kwargs["epochs"] = local_epochs
    elif model_type == "small_mlp":
        model_type = "federated_mlp"
        kwargs["epochs"] = local_epochs
    model = create_model(model_type, **kwargs).initialize(input_dim)
    if parameters is not None:
        model.set_parameters(copy.deepcopy(parameters))
    return model


def run_federated_method(
    dataset,
    partition,
    method,
    policy,
    model_type,
    rounds,
    local_epochs,
    seed,
    minimum_group_samples=10,
    attack_type="none",
    malicious_client_ratio=0.0,
    fairfed_beta=1.0,
    round_infrastructure=None,
    remote_trainer=None,
):
    if method not in {"B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7"}:
        raise FederatedExperimentError(
            f"{method} requires infrastructure integration not provided by "
            "the local federated executor"
        )
    if method == "B2" and round_infrastructure is None:
        raise FederatedExperimentError(
            "B2 requires the strict Kubo and ledger infrastructure adapter"
        )
    if method in {"B4", "B7"} and round_infrastructure is None:
        raise FederatedExperimentError(
            f"{method} requires the strict Kubo, V2 Groth16, signed-decision, and ledger adapter"
        )
    prepared = prepare_federated_data(dataset)
    supported_attacks = {"none", "label_flip", "sign_flip", "random_weights"}
    if attack_type not in supported_attacks:
        raise FederatedExperimentError(f"Unsupported attack type: {attack_type}")
    if not 0 <= malicious_client_ratio < 1:
        raise FederatedExperimentError(
            "malicious_client_ratio must be in [0, 1)"
        )
    input_dim = prepared.train_features.shape[1]
    global_model = _new_model(model_type, seed, local_epochs, input_dim)
    global_parameters = global_model.get_parameters()
    local_splits = [
        _local_train_evaluation_split(
            indices,
            prepared.train_labels,
            prepared.train_protected,
            seed + client_id,
        )
        for client_id, indices in enumerate(partition.client_indices)
    ]
    if remote_trainer is not None:
        remote_trainer.prepare(prepared, local_splits)
    malicious_count = (
        0
        if attack_type == "none"
        else max(1, int(round(len(local_splits) * malicious_client_ratio)))
    )
    attack_rng = np.random.default_rng(seed + 1_000_003)
    malicious_clients = set(
        attack_rng.choice(
            len(local_splits), size=malicious_count, replace=False
        ).tolist()
    )
    round_rows = []
    client_rows = []
    stage_rows = []
    fairfed_raw_weights = None
    started = time.perf_counter()
    for round_id in range(1, rounds + 1):
        updates = []
        fairfed_metrics = {}
        metrics_by_client = {}
        for client_id, (train_indices, evaluation_indices) in enumerate(local_splits):
            local_started = time.perf_counter()
            is_malicious = client_id in malicious_clients
            local_model = _new_model(
                model_type,
                seed + client_id,
                local_epochs,
                input_dim,
                global_parameters,
            )
            if method == "B5":
                if remote_trainer is None:
                    fairfed_metrics[str(client_id)] = _model_metrics(
                        global_model,
                        prepared.train_features[evaluation_indices],
                        prepared.train_labels[evaluation_indices],
                        prepared.train_protected[evaluation_indices],
                        dataset,
                        minimum_group_samples,
                    )
                else:
                    fairfed_metrics[str(client_id)] = remote_trainer.evaluate(
                        client_id=client_id,
                        round_id=round_id,
                        global_parameters=global_parameters,
                        model_type=model_type,
                        seed=seed + client_id,
                        dataset=dataset,
                        minimum_group_samples=minimum_group_samples,
                    )
            valid = len(np.unique(prepared.train_labels[train_indices])) == 2
            if valid:
                local_training_ms = None
                metric_timings = {}
                if remote_trainer is None:
                    training_labels = prepared.train_labels[train_indices]
                    if is_malicious and attack_type == "label_flip":
                        training_labels = 1 - training_labels
                    training_started = time.perf_counter()
                    local_model.train_local(
                        prepared.train_features[train_indices],
                        training_labels,
                    )
                    local_training_ms = (
                        time.perf_counter() - training_started
                    ) * 1000
                    metrics = _model_metrics(
                        local_model,
                        prepared.train_features[evaluation_indices],
                        prepared.train_labels[evaluation_indices],
                        prepared.train_protected[evaluation_indices],
                        dataset,
                        minimum_group_samples,
                        timing_sink=metric_timings,
                    )
                    parameters = tuple(local_model.get_parameters())
                else:
                    remote_result = remote_trainer.train(
                        client_id=client_id,
                        round_id=round_id,
                        global_parameters=global_parameters,
                        model_type=model_type,
                        seed=seed + client_id,
                        local_epochs=local_epochs,
                        dataset=dataset,
                        minimum_group_samples=minimum_group_samples,
                        label_flip=is_malicious and attack_type == "label_flip",
                    )
                    metrics = remote_result["metrics"]
                    parameters = remote_result["parameters"]
                    local_training_ms = remote_result.get("worker_runtime_ms")
                decision = evaluate_policy(metrics, policy, round_id)
                if is_malicious and attack_type == "sign_flip":
                    parameters = tuple(-value for value in parameters)
                elif is_malicious and attack_type == "random_weights":
                    parameters = tuple(
                        attack_rng.normal(size=np.asarray(value).shape)
                        for value in parameters
                    )
            else:
                local_training_ms = 0.0
                metric_timings = {
                    "local_evaluation_ms": 0.0,
                    "fairness_computation_ms": 0.0,
                }
                metrics = None
                decision = {
                    "approved": False,
                    "reasons": ["local training split contains only one class"],
                }
                parameters = tuple(global_parameters)
            for stage, duration in (
                ("local_training", local_training_ms),
                ("local_evaluation", metric_timings.get("local_evaluation_ms")),
                (
                    "fairness_computation",
                    metric_timings.get("fairness_computation_ms"),
                ),
            ):
                if duration is not None:
                    stage_rows.append(
                        {
                            "stage": stage,
                            "round": round_id,
                            "client_id": client_id,
                            "duration_ms": duration,
                            "evidence_type": "measured",
                        }
                    )
            updates.append(
                ClientUpdate(
                    client_id=str(client_id),
                    parameters=parameters,
                    sample_count=len(train_indices),
                    valid=valid,
                    policy_approved=decision["approved"],
                )
            )
            if metrics is not None:
                metrics_by_client[str(client_id)] = metrics
            client_rows.append(
                {
                    "method": method,
                    "round": round_id,
                    "client_id": client_id,
                    "attack_type": attack_type,
                    "malicious_client": is_malicious,
                    "train_samples": len(train_indices),
                    "evaluation_samples": len(evaluation_indices),
                    "valid_update": valid,
                    "approved": decision["approved"],
                    "accuracy": None if metrics is None else metrics["accuracy"],
                    "macro_f1": None if metrics is None else metrics["macro_f1"],
                    "demographic_parity_gap": None
                    if metrics is None
                    else metrics["demographic_parity_gap"],
                    "equal_opportunity_gap": None
                    if metrics is None
                    else metrics["equal_opportunity_gap"],
                    "equalized_odds_gap": None
                    if metrics is None
                    else metrics["equalized_odds_gap"],
                    "subgroup_accuracy_gap": None
                    if metrics is None
                    else metrics["subgroup_accuracy_gap"],
                    "undefined_metrics": ""
                    if metrics is None
                    else ",".join(sorted(metrics["undefined_metrics"])),
                    "runtime_ms": (time.perf_counter() - local_started) * 1000,
                }
            )
        if method in {"B4", "B7"}:
            infrastructure_approval = round_infrastructure.prepare_round(
                round_id=round_id,
                updates=updates,
                client_metrics=metrics_by_client,
                policy=policy,
            )
            approved_clients = set(infrastructure_approval["approved_clients"])
            retrieved_parameters = infrastructure_approval["retrieved_parameters"]
            updates = [
                replace(
                    update,
                    parameters=retrieved_parameters.get(
                        update.client_id, update.parameters
                    ),
                    policy_approved=update.client_id in approved_clients,
                    proof_verified=update.client_id in approved_clients,
                    artifact_binding_valid=update.client_id in approved_clients,
                    decision_signed=True,
                    on_chain_approved=update.client_id in approved_clients,
                )
                for update in updates
            ]
        try:
            aggregation_started = time.perf_counter()
            fairfed_diagnostics = None
            if method == "B5":
                selected, exclusions = eligible_updates(method, updates)
                selected_metrics = {
                    update.client_id: fairfed_metrics[update.client_id]
                    for update in selected
                }
                previous = (
                    None
                    if fairfed_raw_weights is None
                    else {
                        update.client_id: fairfed_raw_weights[update.client_id]
                        for update in selected
                    }
                )
                fairfed_diagnostics = fairfed_weights(
                    selected,
                    selected_metrics,
                    beta=fairfed_beta,
                    previous_raw_weights=previous,
                )
                fairfed_raw_weights = fairfed_diagnostics["raw_weights"]
                aggregation = aggregate_for_method(
                    method,
                    updates,
                    aggregation_weights=fairfed_diagnostics["weights"],
                )
            else:
                aggregation = aggregate_for_method(method, updates)
            global_parameters = aggregation["parameters"]
            aggregation_status = "updated"
        except AggregationError as exc:
            if "empty update set" not in str(exc):
                raise
            aggregation = {
                "parameters": global_parameters,
                "included_clients": [],
                "excluded_clients": {
                    update.client_id: (
                        "invalid_update"
                        if not update.valid
                        else "policy_not_approved"
                    )
                    for update in updates
                },
            }
            aggregation_status = "skipped_no_eligible_clients"
        stage_rows.append(
            {
                "stage": "aggregation",
                "round": round_id,
                "client_id": None,
                "duration_ms": (time.perf_counter() - aggregation_started) * 1000,
                "evidence_type": "measured",
            }
        )
        global_model.set_parameters(global_parameters)
        validation = _model_metrics(
            global_model,
            prepared.validation_features,
            prepared.validation_labels,
            prepared.validation_protected,
            dataset,
            minimum_group_samples,
        )
        if round_infrastructure is not None:
            round_infrastructure.record_round(
                round_id=round_id,
                updates=updates,
                client_metrics=metrics_by_client,
                global_parameters=global_parameters,
                global_metrics=validation,
                included_clients=aggregation["included_clients"],
            )
        round_rows.append(
            {
                "method": method,
                "round": round_id,
                "aggregation_status": aggregation_status,
                "included_clients": len(aggregation["included_clients"]),
                "excluded_clients": len(aggregation["excluded_clients"]),
                "approval_rate": len(aggregation["included_clients"])
                / len(partition.client_indices),
                "global_accuracy": validation["accuracy"],
                "global_macro_f1": validation["macro_f1"],
                "global_demographic_parity_gap": validation[
                    "demographic_parity_gap"
                ],
                "global_equal_opportunity_gap": validation[
                    "equal_opportunity_gap"
                ],
                "global_equalized_odds_gap": validation["equalized_odds_gap"],
                "global_subgroup_accuracy_gap": validation[
                    "subgroup_accuracy_gap"
                ],
                "fairfed_beta": None
                if fairfed_diagnostics is None
                else fairfed_diagnostics["beta"],
                "fairfed_global_equal_opportunity_difference": None
                if fairfed_diagnostics is None
                else fairfed_diagnostics[
                    "global_equal_opportunity_difference"
                ],
                "fairfed_mean_delta": None
                if fairfed_diagnostics is None
                else fairfed_diagnostics["mean_delta"],
                "fairfed_weights": None
                if fairfed_diagnostics is None
                else fairfed_diagnostics["weights"],
            }
        )
    final_test_timings = {}
    test_metrics = _model_metrics(
        global_model,
        prepared.test_features,
        prepared.test_labels,
        prepared.test_protected,
        dataset,
        minimum_group_samples,
        timing_sink=final_test_timings,
    )
    for stage, duration in final_test_timings.items():
        stage_rows.append(
            {
                "stage": f"final_{stage.removesuffix('_ms')}",
                "round": rounds,
                "client_id": None,
                "duration_ms": duration,
                "evidence_type": "measured",
            }
        )
    infrastructure = (
        None if round_infrastructure is None else round_infrastructure.finalize()
    )
    return {
        "method": method,
        "round_metrics": round_rows,
        "client_metrics": client_rows,
        "test_metrics": test_metrics,
        "runtime_ms": (time.perf_counter() - started) * 1000,
        "stage_timings": stage_rows,
        "final_parameters": global_parameters,
        "infrastructure": infrastructure,
        "remote_training": None
        if remote_trainer is None
        else remote_trainer.evidence(),
    }
