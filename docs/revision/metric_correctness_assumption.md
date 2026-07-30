# Metric Correctness Assumption

V2 proves threshold compliance for supplied circuit-compatible metric values.
Metric computation remains outside the circuit.

The implementation reduces substitution risk by binding canonical
`metrics.json` and `manifest.json` digests and by independently applying the
same versioned policy in the verifier service. It still assumes the metric
producer used the documented group definitions, favorable label, evaluation
split, and formulas honestly.

A future circuit could prove selected rates from committed aggregate confusion
counts. That would narrow this assumption but would still not prove dataset
authenticity or honest model training.
