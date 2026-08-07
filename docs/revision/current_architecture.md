# Current Architecture

The implementation consists of:

1. Three deterministic synthetic client partitions.
2. Local logistic-regression training and group metric evaluation.
3. Groth16 witness/proof generation with local snarkjs verification.
4. JSON model, metric, proof, public-input, metadata, and manifest artifacts.
5. Kubo HTTP/CLI storage when available, with a local SHA-256 fallback.
6. A local Hardhat deployment of a verifier contract and ethical ledger.
7. Signed verifier decisions in the default end-to-end runner.
8. Approved-only weighted FedAvg and global artifact publication.
9. Round closure, aggregation start, publication, and archival.

The architecture is a research implementation. It is not a distributed
production deployment and has no external security audit.

