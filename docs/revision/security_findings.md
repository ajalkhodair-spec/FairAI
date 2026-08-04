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

Direct V2 Groth16 generation and Solidity pairing verification now use pinned,
checksum-verified artifacts. Thirty valid proofs and six negative binding cases
were exercised in the proof benchmark, and contract tests reject invalid proofs,
tampered signed decisions, replay, expiry, revocation, and context mismatch. The
experimental phase-2 ZKey has one contributor; no production ceremony or external
cryptographic audit is claimed.

Sources:

- `outputs/major_revision/security-evidence/attack_matrix.csv`
- `outputs/major_revision/adversarial-5seed-e8733cb/metrics/test_metrics.csv`
- `hardhat/test/FairAIEthicalLedger.js`
- `hardhat/test/FairAISignedVerifierV2.js`
- `hardhat/test/FairAIV2CompositeVerifier.js`
- `tests/test_revision_binding.py`
- `outputs/revision_audit/v2_proof_benchmark.json`
