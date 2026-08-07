# Direct Groth16 Verification Status

V2 compiles with the pinned Circom 2.1.6 build: 751 constraints, 19 public
inputs, 2 private inputs, and 2 public outputs. The phase-2 Powers of Tau passes
`snarkjs powersoftau verify`, and the generated ZKey passes verification against
the R1CS and ceremony artifact.

The repository contains checksum-manifested R1CS, WASM, ZKey, verification key,
generated Solidity verifier, and acceptance proof fixture. Thirty local proof
runs verified; five out-of-policy witnesses and one tampered public-signal case
were rejected. The measured summary is
`outputs/revision_audit/v2_proof_benchmark.json`.

The `FairAIV2CompositeVerifier` requires both the generated Groth16 verifier and
a domain-separated EIP-712 decision. It binds node, round, policy version,
nonce, and reduced SHA-256 manifest/metrics fields. The ledger consumes signed
nonces, rejects context substitution, and records approved and rejected
outcomes.

The current phase-2 setup has one experimental contributor. It is suitable for
validated engineering experiments, not production deployment; a governed
multi-party ceremony is required before a production trust claim.
