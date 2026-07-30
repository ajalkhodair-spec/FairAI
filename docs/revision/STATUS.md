# Major Revision Status

- Current phase: Phase 2, formal legacy reproduction
- Completed: Phase 0 audit, baseline commit, annotated submitted-state tag,
  revision branch, strict-Kubo diagnostic legacy reproduction, G1
  configuration runner, schemas, manifests, Make targets, and CI smoke step
- Tests passed:
  - Python: 10 tests
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
- Next action: run the legacy configuration as three independently manifested
  trials and generate the formal reproduction package
- Latest commit hash: `68e782ed46f2778f11c5cca61745c9b078a3fbba`
- Latest output path: `outputs/revision_audit/baseline_manifest.json`
