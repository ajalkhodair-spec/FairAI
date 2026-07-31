# Security Findings

The A1-A14 matrix separates enforcement tests, measured poisoning outcomes, and
known undetected threats. Contract and binding tests reject unauthorized
signers, changed signed fields, replayed digests or nonces, unregistered nodes,
duplicate submissions, duplicate CIDs, unavailable artifacts, byte mismatches,
and post-proof metrics changes.

The five-seed poisoning suite uses 10 Adult clients, five rounds, joint
Dirichlet alpha 0.3 partitions, and a deterministic 20% malicious cohort.
Random weights, sign-flipped updates, and label-flipped local training are
compared under FedAvg and coordinate-wise median. These attacks are evaluated
for impact; they are not automatically classified as invalid merely because a
client is malicious.

Direct V2 Groth16 rejection evidence remains blocked by the missing Circom 2.1.6
toolchain artifacts. The legacy/mock invalid-proof path is tested, but it is not
reported as direct V2 pairing-verifier evidence.

Sources:

- `outputs/major_revision/security-evidence/attack_matrix.csv`
- `outputs/major_revision/adversarial-5seed-e8733cb/metrics/test_metrics.csv`
- `hardhat/test/FairAIEthicalLedger.js`
- `hardhat/test/FairAISignedVerifierV2.js`
- `tests/test_revision_binding.py`
