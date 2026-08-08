# Direct Verifier Evidence Boundary

The public evidence package contains:

- `outputs/revision_audit/v2_proof_benchmark.json`, reporting 30 valid local
  proof generations/verifications and six rejected negative cases;
- `outputs/revision_audit/v2_gas_summary.csv`, reporting `n=30` for
  `verify_v2_groth16`, with 348,811 gas for every summarized execution;
- `outputs/revision_audit/v2_gas_run_manifest.json`, binding the gas benchmark
  to its source and local environment.

It does not contain transaction-level raw direct-verifier receipts with
transaction hashes. Therefore the supported wording is:

> Direct Solidity verification consumed 348,811 gas in each of 30 summarized
> local Hardhat verification executions.

The package does not support the stronger wording that 30 independently
archived on-chain transaction receipts are available. The measurements are
local Hardhat evidence, not public-chain latency or cost measurements.
