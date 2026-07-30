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
| 4 | IID/non-IID partitioning and entropy | Deterministic partitions and entropy outputs | Pending |
| 5 | Group fairness metrics and policy engine | DP, EO, EOdds, SAG and policy tests | Pending |
| 6 | Baselines and ablations | B0-B4, B6-B7; B5 or documented blocker | Pending |
| 7 | V2 proof binding | Versioned circuit, canonical digests, negative tests | Pending |
| 8 | Verifier security | EIP-712, replay, expiry, revocation, compromise test | Pending |
| 9 | Expanded experiment suites | R1-R7 measured with manifests | Pending |
| 10 | Statistics and result freeze | Workbook, CSVs, tables, figures, evidence map | Pending |
| 11 | Clean reproduction and release | G6 clean clone and release package | Pending |

## Dependencies

- Phase 1 depends on Phase 0 classification.
- Phase 2 requires compatible Circom, snarkjs, Powers of Tau, Hardhat, and Kubo.
- Real-data phases require verified sources and documented licensing.
- Full FairAI comparisons require strict Kubo and cryptographic artifacts.
- Results freeze requires all mandatory suites to be complete or explicitly blocked.

## Current Next Action

Begin Phase 4: deterministic IID and Dirichlet non-IID client partitioning,
minimum-size enforcement, normalized entropy, and partition evidence.
