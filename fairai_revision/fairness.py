from dataclasses import dataclass

import numpy as np


class FairnessMetricError(ValueError):
    pass


@dataclass(frozen=True)
class Rate:
    value: float | None
    numerator: int
    denominator: int
    reason: str | None = None


def _rate(numerator, denominator, label):
    if denominator == 0:
        return Rate(
            value=None,
            numerator=int(numerator),
            denominator=0,
            reason=f"{label} denominator is zero",
        )
    return Rate(
        value=float(numerator / denominator),
        numerator=int(numerator),
        denominator=int(denominator),
    )


def _rate_dict(rate):
    return {
        "value": rate.value,
        "numerator": rate.numerator,
        "denominator": rate.denominator,
        "reason": rate.reason,
    }


def _group_metrics(y_true, y_pred, mask, favorable_label):
    truth = y_true[mask]
    predicted = y_pred[mask]
    positive_truth = truth == favorable_label
    negative_truth = ~positive_truth
    positive_prediction = predicted == favorable_label
    correct = truth == predicted
    count = len(truth)
    return {
        "count": count,
        "predicted_positive_rate": _rate_dict(
            _rate(positive_prediction.sum(), count, "predicted-positive rate")
        ),
        "true_positive_rate": _rate_dict(
            _rate(
                (positive_prediction & positive_truth).sum(),
                positive_truth.sum(),
                "true-positive rate",
            )
        ),
        "false_positive_rate": _rate_dict(
            _rate(
                (positive_prediction & negative_truth).sum(),
                negative_truth.sum(),
                "false-positive rate",
            )
        ),
        "accuracy": _rate_dict(_rate(correct.sum(), count, "accuracy")),
        "false_negative_rate": _rate_dict(
            _rate(
                ((~positive_prediction) & positive_truth).sum(),
                positive_truth.sum(),
                "false-negative rate",
            )
        ),
        "true_negative_rate": _rate_dict(
            _rate(
                ((~positive_prediction) & negative_truth).sum(),
                negative_truth.sum(),
                "true-negative rate",
            )
        ),
    }


def _difference(left, right, metric, undefined):
    if left is None or right is None:
        undefined[metric] = f"{metric} requires defined rates for both comparison groups"
        return None
    return abs(float(left) - float(right))


def evaluate_group_fairness(
    y_true,
    y_pred,
    protected,
    privileged_value,
    unprivileged_value,
    favorable_label=1,
    minimum_group_samples=1,
):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    protected = np.asarray(protected)
    if not (y_true.ndim == y_pred.ndim == protected.ndim == 1):
        raise FairnessMetricError("Inputs must be one-dimensional")
    if not (len(y_true) == len(y_pred) == len(protected)):
        raise FairnessMetricError("Inputs must have equal lengths")
    if len(y_true) == 0:
        raise FairnessMetricError("Inputs must not be empty")
    if minimum_group_samples < 1:
        raise FairnessMetricError("minimum_group_samples must be positive")
    if privileged_value == unprivileged_value:
        raise FairnessMetricError("Comparison group values must be distinct")

    groups = sorted(np.unique(protected).tolist(), key=str)
    group_metrics = {
        str(group): _group_metrics(
            y_true, y_pred, protected == group, favorable_label
        )
        for group in groups
    }
    privileged = group_metrics.get(str(privileged_value))
    unprivileged = group_metrics.get(str(unprivileged_value))
    undefined = {}
    for label, metrics in (
        ("privileged", privileged),
        ("unprivileged", unprivileged),
    ):
        if metrics is None:
            undefined["comparison_groups"] = f"{label} group is absent"
        elif metrics["count"] < minimum_group_samples:
            undefined["comparison_groups"] = (
                f"{label} group has {metrics['count']} samples; "
                f"minimum is {minimum_group_samples}"
            )

    if "comparison_groups" in undefined:
        dp_gap = eo_gap = equalized_odds_gap = None
    else:
        dp_gap = _difference(
            unprivileged["predicted_positive_rate"]["value"],
            privileged["predicted_positive_rate"]["value"],
            "demographic_parity_gap",
            undefined,
        )
        eo_gap = _difference(
            unprivileged["true_positive_rate"]["value"],
            privileged["true_positive_rate"]["value"],
            "equal_opportunity_gap",
            undefined,
        )
        tpr_gap = eo_gap
        fpr_gap = _difference(
            unprivileged["false_positive_rate"]["value"],
            privileged["false_positive_rate"]["value"],
            "false_positive_rate_gap",
            undefined,
        )
        if tpr_gap is None or fpr_gap is None:
            equalized_odds_gap = None
            undefined["equalized_odds_gap"] = (
                "equalized-odds gap requires defined TPR and FPR for both groups"
            )
        else:
            equalized_odds_gap = max(tpr_gap, fpr_gap)

    eligible_accuracies = [
        metrics["accuracy"]["value"]
        for metrics in group_metrics.values()
        if metrics["count"] >= minimum_group_samples
        and metrics["accuracy"]["value"] is not None
    ]
    if len(eligible_accuracies) < 2:
        subgroup_accuracy_gap = None
        undefined["subgroup_accuracy_gap"] = (
            "subgroup-accuracy gap requires at least two adequately sized groups"
        )
    else:
        subgroup_accuracy_gap = max(eligible_accuracies) - min(eligible_accuracies)

    return {
        "schema_version": "fairai.group_fairness.v1",
        "sample_count": len(y_true),
        "favorable_label": favorable_label,
        "privileged_value": str(privileged_value),
        "unprivileged_value": str(unprivileged_value),
        "minimum_group_samples": minimum_group_samples,
        "accuracy": float(np.mean(y_true == y_pred)),
        "demographic_parity_gap": dp_gap,
        "equal_opportunity_gap": eo_gap,
        "equalized_odds_gap": equalized_odds_gap,
        "subgroup_accuracy_gap": subgroup_accuracy_gap,
        "groups": group_metrics,
        "undefined_metrics": undefined,
    }
