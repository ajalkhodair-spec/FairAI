# Major Revision Status

- Current phase: Phase 11, clean reproduction and release packaging
- Completed: Phase 0 audit, baseline commit, annotated submitted-state tag,
  revision branch, strict-Kubo diagnostic legacy reproduction, G1
  configuration runner, schemas, manifests, Make targets, CI smoke step, and
  formal three-trial legacy evidence package, checksum-pinned Adult and COMPAS
  acquisition, train-only preprocessing, and common logistic-regression and
  small-MLP model interfaces, a deterministic parameter-transfer federated MLP,
  deterministic IID and Dirichlet client
  partitioning, minimum-size enforcement, canonical partition checksums, and
  normalized entropy exports, protected-group DP/EO/equalized-odds/SAG metrics,
  explicit undefined results, versioned round-bounded approval policies, and
  real-data multi-round B0/B1/B3 engineering-validation runs, paired ten-seed
  Adult/COMPAS statistics, federated MLP, client scaling, heterogeneity,
  threshold sensitivity, deterministic poisoning, 2,825 Hardhat gas receipts,
  expanded statistics, security/privacy/ethics/complexity evidence, workbook,
  and figures
- Tests passed:
  - Python: 57 tests
  - Solidity: 15 tests
  - Hardhat compile: 7 contracts
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
  - Docker socket access is unavailable to this task, so strict two-node Kubo
    measurements cannot be generated in the current execution environment
- Next action: clean-clone verification and external resolution of BLK-001,
  BLK-002, BLK-003, and BLK-004
- Latest commit hash: `4221f16`
- Latest output paths:
  - `outputs/major_revision/adult-core-10seed-e01b72a`
  - `outputs/major_revision/compas-core-10seed-e01b72a`
  - `outputs/major_revision/core-statistics-a8fe359`
  - `outputs/major_revision/expanded-analysis-466cb07`
  - `outputs/major_revision/gas-benchmark-30rep-6f80450`
  - `outputs/major_revision/FairAI_Major_Revision_Results.xlsx`
