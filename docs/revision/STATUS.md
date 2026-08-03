# Major Revision Status

- Active branch: `major-revision-azure`
- Upgrade basis: exact reviewer reports and submitted manuscript, bounded by
  `docs/revision/acceptance_scope.md`
- Frozen pre-Azure evidence: commit `62d8dd3`, recorded in
  `outputs/revision_audit/current_evidence_freeze.json`
- Current work: acceptance-critical baseline and infrastructure integration
  gaps; no Azure resources have been created

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
- Tests passed before the current branch:
  - Python: 59 tests in the clean-clone evidence
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
  - Docker socket API calls remain denied after explicit sandbox grants and no
    Kubo ports are listening, so the new strict B2 adapter cannot yet generate
    measured two-peer evidence in this task
- Clean-clone status:
  - no-local clone passed;
  - independent npm installation passed;
  - 59 Python and 15 Solidity tests passed with the verified Python environment;
  - smoke and a 10-seed Adult run passed;
  - CSV, LaTeX, and SVG regeneration was byte-for-byte reproducible;
  - fresh pip installation remained blocked by sandbox DNS
- Current-branch verification:
  - 61 Python and 20 Solidity tests pass on the current branch
  - 30/30 V2 proofs verify and six negative cryptographic cases reject
  - the real V2 proof passes the composite Groth16 plus EIP-712 ledger path;
    context substitution, replay, and rejected-decision recording are tested
  - the B2-only verifier and multi-round ledger runner compile
  - B2 unit boundaries pass; real Kubo execution is pending the Docker boundary
- Next action: run strict B2/B4/B7 Kubo integration as soon as Docker is
  reachable, then execute the reviewer-derived local and Azure matrices
- Latest implementation commit hash: `846a068`
- Latest results/reproducibility commit hash: `f62a3ad`
- Latest output paths:
  - `outputs/major_revision/adult-core-10seed-e01b72a`
  - `outputs/major_revision/compas-core-10seed-e01b72a`
  - `outputs/major_revision/core-statistics-bootstrap`
  - `outputs/major_revision/expanded-analysis-bootstrap-aae4091`
  - `outputs/major_revision/gas-throughput-30rep-7dff9b5`
  - `outputs/major_revision/FairAI_Major_Revision_Results.xlsx`
