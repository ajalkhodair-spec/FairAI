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
| 6 | Baselines and ablations | B0-B7 implemented and reference-tested | Partial evidence: B0/B1/B3/B5/B6 measured; B2/B4/B7 await strict Kubo runs |
| 7 | V2 proof binding | Versioned circuit, canonical digests, generated artifacts, negative tests | Complete bounded implementation: 30 proofs, negative cases, direct verifier tests and 30 gas receipts |
| 8 | Verifier security | EIP-712, replay, expiry, revocation, compromise test | Complete |
| 9 | Expanded experiment suites | R1-R7 measured with manifests | Partial: FairFed and algorithmic 3-50 client scaling complete; strict Kubo and Azure matrix pending |
| 10 | Statistics and result freeze | Workbook, CSVs, tables, figures, evidence map | Complete for available evidence, including bootstrap CIs and local throughput |
| 11 | Clean reproduction and release | G6 clean clone and release package | Partial: source/tests/Adult/report validated; Python install, public remote, and Docker blocked |

## Dependencies

- Phase 1 depends on Phase 0 classification.
- Phase 2 requires compatible Circom, snarkjs, Powers of Tau, Hardhat, and Kubo.
- Real-data phases require verified sources and documented licensing.
- Full FairAI comparisons require strict Kubo and cryptographic artifacts.
- Results freeze requires all mandatory suites to be complete or explicitly blocked.

## Current Next Action

The pre-Azure evidence is frozen at commit `62d8dd3` by
`outputs/revision_audit/current_evidence_freeze.json`. Work continues on branch
`major-revision-azure` in this order:

1. run strict Kubo B2/B4/B7 suites when two peers are available;
2. deploy and measure the bounded multi-host Azure matrix;
3. add recovery, concurrency, and infrastructure cost evidence;
4. freeze the complete result package;
5. repeat anonymous clean-clone validation.

See `docs/revision/acceptance_scope.md` for the reviewer-derived scope boundary.
