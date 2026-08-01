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
  240 local throughput scenarios, deterministic bootstrap statistics,
  security/privacy/ethics/complexity evidence, exact publication CSVs,
  workbook, LaTeX tables, and 300-dpi figures
- Tests passed:
  - Python: 58 tests
  - Solidity: 15 tests
  - Hardhat compile: 7 contracts
  - ZKey verification against R1CS and Powers of Tau
  - strict-Kubo three-trial legacy reproduction
- Tests failed:
  - first end-to-end attempt stopped on the intentionally absent Powers of Tau
    file; rerun succeeded with an externally supplied, hash-recorded artifact
  - first concurrent throughput attempt failed because one signer could not
    queue nonces under Hardhat automining; the failed manifest was preserved,
    distinct authorized signers were used, and the 30-repetition rerun passed
- Active blockers:
  - local repository has no configured remote
  - expected prompt URL returned 404 to anonymous access; an older local
    checkout points to `https://github.com/ajalkhodair-spec/FairAI.git`, but
    the active revision repository is not connected to that remote
  - GitHub CLI token is invalid
  - local `circom` reports version 0.5.46 while regeneration requires a
    compatible Circom 2 binary
  - Powers of Tau is external and needs a documented acquisition/checksum flow
  - Docker socket access is unavailable to this task, so strict two-node Kubo
    measurements cannot be generated in the current execution environment
- Clean-clone status:
  - no-local clone passed;
  - independent npm installation passed;
  - 59 Python and 15 Solidity tests passed with the verified Python environment;
  - smoke and a 10-seed Adult run passed;
  - CSV, LaTeX, and SVG regeneration was byte-for-byte reproducible;
  - fresh pip installation remained blocked by sandbox DNS
- Next action: external resolution of BLK-001, BLK-002, BLK-003, and BLK-004
- Latest implementation commit hash: `846a068`
- Latest results/reproducibility commit hash: `f62a3ad`
- Latest output paths:
  - `outputs/major_revision/adult-core-10seed-e01b72a`
  - `outputs/major_revision/compas-core-10seed-e01b72a`
  - `outputs/major_revision/core-statistics-bootstrap`
  - `outputs/major_revision/expanded-analysis-bootstrap-aae4091`
  - `outputs/major_revision/gas-throughput-30rep-7dff9b5`
  - `outputs/major_revision/FairAI_Major_Revision_Results.xlsx`
