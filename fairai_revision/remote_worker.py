import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from .fairness import evaluate_group_fairness
from .federated import _new_model


def execute_training_request(bundle_path, request):
    started = time.perf_counter()
    with np.load(bundle_path, allow_pickle=False) as bundle:
        train_features = bundle["train_features"]
        train_labels = bundle["train_labels"]
        evaluation_features = bundle["evaluation_features"]
        evaluation_labels = bundle["evaluation_labels"]
        evaluation_protected = bundle["evaluation_protected"]
    model = _new_model(
        request["model_type"],
        request["seed"],
        request["local_epochs"],
        train_features.shape[1],
        tuple(np.asarray(value, dtype=float) for value in request["global_parameters"]),
    )
    operation = request.get("operation", "train")
    if operation == "train":
        labels = train_labels
        if request.get("label_flip", False):
            labels = 1 - labels
        model.train_local(train_features, labels)
    elif operation != "evaluate":
        raise ValueError(f"Unsupported remote operation: {operation}")
    predictions = model.predict(evaluation_features)
    metrics = evaluate_group_fairness(
        evaluation_labels,
        predictions,
        evaluation_protected,
        privileged_value=request["privileged_value"],
        unprivileged_value=request["unprivileged_value"],
        favorable_label=request["favorable_label"],
        minimum_group_samples=request["minimum_group_samples"],
    )
    from sklearn.metrics import f1_score

    metrics["macro_f1"] = float(
        f1_score(evaluation_labels, predictions, average="macro")
    )
    return {
        "schema_version": "fairai.remote_training_response.v1",
        "parameters": [value.tolist() for value in model.get_parameters()],
        "metrics": metrics,
        "worker_runtime_ms": (time.perf_counter() - started) * 1000,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Execute one staged FairAI client update")
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args(argv)
    request = json.load(sys.stdin)
    result = execute_training_request(Path(args.bundle), request)
    json.dump(result, sys.stdout, sort_keys=True, allow_nan=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
