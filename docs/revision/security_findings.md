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

A second strict suite executes B4 and B7 with five clients, three rounds, three
paired seeds, and the same 20% malicious-client ratio. All 24 executions use
native Kubo 0.29.0, the V2 Groth16/composite-verifier path, and the Solidity
ledger. Across 72 rounds, all 2,664 IPFS retrievals were byte-verified; 209 of
360 submissions generated proofs and were approved on-chain. Two rounds were
cancelled because no model was eligible.

The fairness gate rejected eight of nine malicious label-flip submissions for
each method. It accepted all nine sign-flip submissions for each method, five
of nine random-weight submissions under B4, and all nine under B7. Mean test
accuracy relative to no attack changed by -0.0319/-0.1837 for label flip,
-0.2910/-0.3208 for sign flip, and -0.2315/-0.1371 for random weights under
B4/B7 respectively. Coordinate median reduced the mean random-weight accuracy
loss, but did not provide general poisoning detection. The proof establishes
the configured fairness relation over supplied metrics; it does not establish
that a model update is benign or correctly derived from local training.

Direct V2 Groth16 generation and Solidity pairing verification now use pinned,
checksum-verified artifacts. Thirty valid proofs and six negative binding cases
were exercised in the proof benchmark, and contract tests reject invalid proofs,
tampered signed decisions, replay, expiry, revocation, and context mismatch. The
experimental phase-2 ZKey has one contributor; no production ceremony or external
cryptographic audit is claimed.

Sources:

- `outputs/major_revision/security-evidence/attack_matrix.csv`
- `outputs/major_revision/adversarial-5seed-e8733cb/metrics/test_metrics.csv`
- `outputs/revision_audit/adversarial-kubo-v2-analysis/adversarial_summary.csv`
- `outputs/revision_audit/adversarial-kubo-v2-analysis/adversarial_approval.csv`
- `outputs/revision_audit/adversarial-kubo-v2-analysis/adversarial_infrastructure.json`
- `outputs/revision_audit/adversarial-kubo-v2-analysis/ledger_receipts.csv`
- `outputs/revision_audit/adversarial-kubo-v2-analysis/proof_decisions.csv`
- `outputs/revision_audit/adversarial-kubo-v2-analysis/ipfs_retrieval_checks.csv`
- `hardhat/test/FairAIEthicalLedger.js`
- `hardhat/test/FairAISignedVerifierV2.js`
- `hardhat/test/FairAIV2CompositeVerifier.js`
- `tests/test_revision_binding.py`
- `outputs/revision_audit/v2_proof_benchmark.json`
