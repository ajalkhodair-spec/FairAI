# Complexity Analysis

Notation:

- `N`: clients
- `R`: communication rounds
- `d`: model parameters
- `m`: tracked artifacts per client
- `B_i`: artifact bytes for client `i`
- `C_circuit`: circuit constraints
- `A_t`: approved clients in round `t`
- `V`: authorized verifier count
- `M`: required signature threshold

Local computation is dominated by model training. For the full-batch logistic
implementation, a useful form is `O(R sum_i E n_i d)`, where `E` is local
epochs and `n_i` is the local sample count. The one-hidden-layer MLP has the
same sample/round structure but `d` includes both dense layers.

Fairness evaluation is linear in evaluated examples. Weighted FedAvg is
`O(|A_t|d)`. The current coordinate-median implementation stacks client
parameters and applies NumPy median per coordinate; its memory is
`O(|A_t|d)`, and a conservative comparison-based time bound is
`O(|A_t|d log |A_t|)`.

Contract submission and reference growth are `O(NRm)` over an experiment.
`getEligibleModelCids` currently scans all round records and then materializes
the approved set, so retrieval is `O(NR + |A_t|)` for the queried round rather
than only `O(|A_t|)`.

IPFS byte-processing work is proportional to artifact size, but network,
chunking, cache, and replication constants require measurement. Those V2
two-peer measurements are blocked by Docker socket access. Direct V2 Groth16
cost is expressed as a function of `C_circuit`; measured constraint, proving,
verification, and pairing-gas values remain blocked until Circom 2.1.6
artifacts are generated.

The machine-readable mapping is
`outputs/major_revision/complexity/complexity_analysis.csv`.
