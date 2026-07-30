# Direct Groth16 Verification Status

The repository preserves a generated legacy Groth16 verifier and adapter, but
the V2 circuit has not yet been compiled with the pinned Circom 2.1.6 toolchain.
Therefore direct on-chain V2 Groth16 verification is unavailable and no V2 gas
or latency result is claimed.

The signed-verifier path performs off-chain proof and artifact checks, then
places a domain-separated decision on-chain. Its on-chain cost is lower than a
pairing verifier but it trusts authorized signer honesty. Direct Groth16 would
remove signature-based proof-validity trust while retaining the off-circuit
metric-correctness and artifact-retrieval assumptions.

Measured comparison is deferred until V2 R1CS/WASM/ZKey generation and the
matching Solidity verifier pass clean-toolchain tests.
