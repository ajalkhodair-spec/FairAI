# Direct Groth16 Verification Status

The repository preserves a generated legacy Groth16 verifier and adapter. The
V2 source compiled successfully with a discovered local Circom 2.1.9 binary:
751 constraints, 19 public inputs, 2 private inputs, and 2 public outputs. This
is a compatibility check, not the pinned Circom 2.1.6 build required by the
toolchain lock.

No checksum-pinned Powers of Tau file or V2 ZKey is available. Therefore direct
on-chain V2 Groth16 verification remains unavailable and no V2 proving,
verification-latency, or pairing-gas result is claimed.

The signed-verifier path performs off-chain proof and artifact checks, then
places a domain-separated decision on-chain. Its on-chain cost is lower than a
pairing verifier but it trusts authorized signer honesty. Direct Groth16 would
remove signature-based proof-validity trust while retaining the off-circuit
metric-correctness and artifact-retrieval assumptions.

Measured comparison is deferred until V2 R1CS/WASM/ZKey generation and the
matching Solidity verifier pass clean-toolchain tests. Compilation hashes and
the exact command are recorded in `docs/revision/v2_compile_check.md`.
