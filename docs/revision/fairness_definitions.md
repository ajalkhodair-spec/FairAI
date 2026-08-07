# Fairness Metrics and Approval Policies

## Outcome Convention

All metrics use the dataset's documented favorable label:

- Adult: income greater than USD 50,000.
- COMPAS: no recidivism within two years.

Protected attributes are retained for evaluation and excluded from model
features by default.

## Group Statistics

For every protected group the evaluator records sample count,
predicted-positive rate, true-positive rate, false-positive rate, accuracy,
false-negative rate, and true-negative rate. Every rate includes its numerator,
denominator, value, and an undefined reason when its denominator is zero.

## Gap Definitions

Demographic parity difference:

```text
DP = |P(predicted favorable | unprivileged)
      - P(predicted favorable | privileged)|
```

Equal opportunity difference:

```text
EO = |TPR_unprivileged - TPR_privileged|
```

Equalized-odds difference:

```text
EOdds = max(
  |TPR_unprivileged - TPR_privileged|,
  |FPR_unprivileged - FPR_privileged|
)
```

Subgroup accuracy gap:

```text
SAG = max(group accuracy) - min(group accuracy)
```

These are protected-group metrics. Per-class accuracy balance is not reported
as demographic parity.

## Undefined Metrics

A comparison metric is `null`, never zero, when a required group is absent,
does not meet the configured minimum size, or has no observations in a required
denominator. The result contains an `undefined_metrics` map explaining each
event.

The production policy default is `reject` for an undefined enabled metric.
Versioned policies may explicitly select `ignore` or `error`; there is no
implicit behavior.

## Policy Semantics

Policy profiles are stored in
`configs/revision/policy_profiles.json` and validated against
`schemas/fairness_policy.schema.json`. Each profile defines:

- minimum accuracy;
- maximum DP, EO, equalized-odds, and subgroup-accuracy gaps;
- a complete enabled-metric mask;
- explicit `AND` semantics;
- undefined-metric behavior;
- an inclusive valid-round range.

The `submitted` profile preserves minimum accuracy `0.62` and maximum DP gap
`0.28`. Lenient, moderate, strict, and multi-metric profiles are bounded
sensitivity settings. Thresholds must be selected before test-set evaluation.

## Verification

```sh
.venv/bin/python -m unittest tests.test_revision_fairness_policy -v
```

The tests include hand-computable confusion-rate examples, missing-denominator
cases, minimum-group-size behavior, threshold boundaries, undefined-policy
behavior, and round validity.
