# FairAI Major Revision Plan

This file is the source of truth for the acceptance-oriented revision.

## Principles

- Preserve the submitted three-node implementation as `legacy_mvp_reproduction`.
- Separate measured, derived, modeled, estimated, and missing evidence.
- Do not broaden claims beyond demonstrated behavior.
- Keep strict Kubo/IPFS scenarios fail-closed.
- Preserve failed runs and Version 1 evidence.
- Require a run manifest for every revision experiment.

## Milestones

| Phase | Scope | Completion gate | Status |
|---|---|---|---|
| 0 | Repository and evidence audit | Audit documents, baseline manifest, targeted tests | Complete |
| 1 | Reproducibility infrastructure | Config runner, schemas, locks, smoke test | Complete |
| 2 | Legacy reproduction | Three deterministic trials and gap report | Complete |
| 3 | Adult/COMPAS and model interfaces | Licensed loaders, checksums, LR and MLP tests | Complete |
| 4 | IID/non-IID partitioning and entropy | Deterministic partitions and entropy outputs | Complete |
| 5 | Group fairness metrics and policy engine | DP, EO, EOdds, SAG and policy tests | Complete |
| 6 | Baselines and ablations | B0-B4, B6-B7; B5 or documented blocker | Partial: B0/B1/B3/B6 measured; B2/B4/B7 infrastructure blocked; B5 documented |
| 7 | V2 proof binding | Versioned circuit, canonical digests, negative tests | Partial: source and negative tests complete; artifacts blocked |
| 8 | Verifier security | EIP-712, replay, expiry, revocation, compromise test | Complete |
| 9 | Expanded experiment suites | R1-R7 measured with manifests | Partial: R2-R6 available evidence complete; strict V2/IPFS portions blocked |
| 10 | Statistics and result freeze | Workbook, CSVs, tables, figures, evidence map | Complete for available evidence, including bootstrap CIs and local throughput |
| 11 | Clean reproduction and release | G6 clean clone and release package | Partial: source/tests/Adult/report validated; Python install, public remote, and Docker blocked |

## Dependencies

- Phase 1 depends on Phase 0 classification.
- Phase 2 requires compatible Circom, snarkjs, Powers of Tau, Hardhat, and Kubo.
- Real-data phases require verified sources and documented licensing.
- Full FairAI comparisons require strict Kubo and cryptographic artifacts.
- Results freeze requires all mandatory suites to be complete or explicitly blocked.

## Current Next Action

Resolve `BLK-001` through `BLK-004`, rerun strict Kubo/V2/FairFed suites, and
repeat the clean-clone protocol from the anonymously accessible public URL.
