# Legacy Diagnostic Reproduction

The Version 1 implementation was run for three trials with strict Kubo/IPFS,
Hardhat, Groth16 proof generation, local snarkjs verification, the signed
verifier path, approved-only weighted FedAvg, global publication, and archival.

## Result

The following values matched the submitted result package:

- Node 1 accuracy: `0.950000`
- Node 1 DP gap: `0.003127`
- Node 2 accuracy: `0.962500`
- Node 2 DP gap: `0.000000`
- Node 3 accuracy: `0.962500`
- Node 3 DP gap: `0.282132`
- approved nodes: `[1, 2]`
- rejected nodes: `[3]`
- global accuracy: `0.938889`
- global DP gap: `0.144269`
- approval rate: `0.666667`
- global publication gas: `449664`

Fresh timing observations:

- mean proof generation: `612.479111 ms`
- mean IPFS retrieval: `0.867476 ms`
- trial runtimes: `3993.614`, `3117.294`, and `3037.353 ms`

Timing differences from the submitted package are retained as measured
environment variation. They are not treated as reproduction failures.

The formal Phase 2 output package will be regenerated through the Phase 1
configuration and manifest infrastructure. This diagnostic run does not replace
that traceable run.

