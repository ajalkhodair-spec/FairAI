# FairFed Baseline Protocol

## Status

Implemented and locally unit-tested. Comparative Adult and COMPAS results must
still be generated under the frozen experiment configuration.

`B5` implements the server weighting update in Algorithm 1 of Ezzeldin et al.,
"FairFed: Enabling Group Fairness in Federated Learning" (AAAI 2023):

1. initialize raw weights from client sample fractions;
2. evaluate the current global model on each client's local evaluation split;
3. derive global signed equal-opportunity difference from aggregated TP and
   positive-label counts;
4. compute each deviation from the global fairness value, falling back to the
   local/global accuracy difference if a client's fairness value is undefined;
5. update raw weights by the published beta-scaled deviation-from-mean rule;
6. normalize the raw weights and aggregate the trained local parameters.

The core configurations freeze `beta = 1.0`. Unit tests cover beta zero,
manually calculated unequal-denominator weights, accuracy fallback, and a
deterministic multi-round execution.

## Claim Boundary

This baseline reproduces the FairFed server aggregation rule. It does not claim
to reproduce every local debiasing method evaluated in the paper. The current
binary tabular protocol uses signed equal-opportunity difference and does not
centralize client records: only sufficient counts are combined. Negative raw
weights are not silently clipped because clipping is absent from the published
equation; every round exports normalized weights and diagnostics for audit.

Primary source: https://ojs.aaai.org/index.php/AAAI/article/view/25911
