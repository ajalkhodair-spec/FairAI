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

IPFS byte-processing work is proportional to artifact size, while network,
chunking, cache, and replication constants are empirical. The local two-peer
suite measures 1 KiB through 10 MiB payloads and concurrency 1 through 20; it
does not estimate WAN or outage-recovery constants. Direct V2 Groth16 cost is a
function of `C_circuit`; witness, proving, off-chain verification, and direct
pairing-verifier gas are measured with the checksum-manifested V2 artifacts.
Their manifest declares Circom 2.1.6; compiler-build provenance is bounded in
`docs/revision/circom_version_reconciliation.md`.

The machine-readable mapping is
`outputs/major_revision/complexity/complexity_analysis.csv`; measured Kubo and
V2 summaries are under `outputs/revision_audit/infrastructure-analysis/` and
`outputs/revision_audit/v2_gas_summary.csv`.
