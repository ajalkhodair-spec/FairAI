# Major Revision Status

- Current phase: Phase 4, client partitioning and entropy
- Completed: Phase 0 audit, baseline commit, annotated submitted-state tag,
  revision branch, strict-Kubo diagnostic legacy reproduction, G1
  configuration runner, schemas, manifests, Make targets, CI smoke step, and
  formal three-trial legacy evidence package, checksum-pinned Adult and COMPAS
  acquisition, train-only preprocessing, and common logistic-regression and
  small-MLP model interfaces
- Tests passed:
  - Python: 16 tests
  - Solidity: 8 tests
  - Hardhat compile: 6 contracts
  - ZKey verification against R1CS and Powers of Tau
  - strict-Kubo three-trial legacy reproduction
- Tests failed:
  - first end-to-end attempt stopped on the intentionally absent Powers of Tau
    file; rerun succeeded with an externally supplied, hash-recorded artifact
- Active blockers:
  - local repository has no configured remote
  - expected public URL returned 404 to anonymous access
  - GitHub CLI token is invalid
  - local `circom` reports version 0.5.46 while regeneration requires a
    compatible Circom 2 binary
  - Powers of Tau is external and needs a documented acquisition/checksum flow
- Next action: implement deterministic IID and Dirichlet non-IID client
  partitioning with minimum-size enforcement and normalized entropy evidence
- Latest commit hash: `854d988`
- Latest output path: `outputs/revision_audit/baseline_manifest.json`
