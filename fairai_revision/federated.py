import copy
import time
from dataclasses import dataclass

import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split

from .aggregation import ClientUpdate, aggregate_for_method
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
):
    predictions = model.predict(features)
    result = evaluate_group_fairness(
        labels,
        predictions,
        protected,
        privileged_value=dataset.privileged_value,
        unprivileged_value=dataset.unprivileged_value,
        favorable_label=dataset.favorable_label,
        minimum_group_samples=minimum_group_samples,
    )
    result["macro_f1"] = float(f1_score(labels, predictions, average="macro"))
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
):
    if method not in {"B0", "B1", "B3", "B6"}:
        raise FederatedExperimentError(
            f"{method} requires infrastructure integration not provided by "
            "the local federated executor"
        )
    prepared = prepare_federated_data(dataset)
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
    round_rows = []
    client_rows = []
    started = time.perf_counter()
    for round_id in range(1, rounds + 1):
        updates = []
        for client_id, (train_indices, evaluation_indices) in enumerate(local_splits):
            local_started = time.perf_counter()
            local_model = _new_model(
                model_type,
                seed + client_id,
                local_epochs,
                input_dim,
                global_parameters,
            )
            valid = len(np.unique(prepared.train_labels[train_indices])) == 2
            if valid:
                local_model.train_local(
                    prepared.train_features[train_indices],
                    prepared.train_labels[train_indices],
                )
                metrics = _model_metrics(
                    local_model,
                    prepared.train_features[evaluation_indices],
                    prepared.train_labels[evaluation_indices],
                    prepared.train_protected[evaluation_indices],
                    dataset,
                    minimum_group_samples,
                )
                decision = evaluate_policy(metrics, policy, round_id)
                parameters = tuple(local_model.get_parameters())
            else:
                metrics = None
                decision = {
                    "approved": False,
                    "reasons": ["local training split contains only one class"],
                }
                parameters = tuple(global_parameters)
            updates.append(
                ClientUpdate(
                    client_id=str(client_id),
                    parameters=parameters,
                    sample_count=len(train_indices),
                    valid=valid,
                    policy_approved=decision["approved"],
                )
            )
            client_rows.append(
                {
                    "method": method,
                    "round": round_id,
                    "client_id": client_id,
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
        aggregation = aggregate_for_method(method, updates)
        global_parameters = aggregation["parameters"]
        global_model.set_parameters(global_parameters)
        validation = _model_metrics(
            global_model,
            prepared.validation_features,
            prepared.validation_labels,
            prepared.validation_protected,
            dataset,
            minimum_group_samples,
        )
        round_rows.append(
            {
                "method": method,
                "round": round_id,
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
            }
        )
    test_metrics = _model_metrics(
        global_model,
        prepared.test_features,
        prepared.test_labels,
        prepared.test_protected,
        dataset,
        minimum_group_samples,
    )
    return {
        "method": method,
        "round_metrics": round_rows,
        "client_metrics": client_rows,
        "test_metrics": test_metrics,
        "runtime_ms": (time.perf_counter() - started) * 1000,
        "final_parameters": global_parameters,
    }
