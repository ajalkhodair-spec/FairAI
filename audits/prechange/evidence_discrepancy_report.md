# Pre-change Evidence Discrepancy Report

**Milestone:** 0, read-only reconciliation  
**Initial and final milestone status:** `NOT_READY`  
**Meaning:** the implementation has not failed; the public software, evidence,
manuscript, and reviewer-response states are not yet one proven authoritative
package.

## Scope preserved

No source, tests, configuration, raw evidence, result workbook, manuscript,
Git ref, remote, GitHub release, or Zenodo record was modified. No experiment
or test suite was run. Only audit files under `audits/prechange/` were created
in an isolated clone based on cached `origin/main`.

## Verified alignment

1. GitHub release `v0.2.1` points to commit `cabcea687ba3d6476f98375617a9100f578aca85`.
2. Zenodo version `10.5281/zenodo.21838695` is published as `v0.2.1`; its archive
   preview root is `ajalkhodair-spec-FairAI-cabcea6` and therefore matches the
   release commit.
3. `v0.2.1` and `major-revision-azure` are ancestors of cached public `main`.
4. The four commits after `v0.2.1` change only `README.md` and `CITATION.cff`.
   Runtime, contracts, IPFS implementation, experiment code, and results are
   identical between the tag and current public `main`.
5. The tracked `outputs/major_revision/release_checksums.sha256` validates 331
   files with 331 OK, zero missing, and zero mismatches.
6. Dirichlet alpha 1.0 is supported by seed/client-level tracked evidence under
   `outputs/revision_audit/entropy-approval-4d97043/`, not merely by config.

## Blocking discrepancies

### D1. The working local repository is stale

The original local checkout is at `ac966fbc...` and reports 75
commits behind cached `origin/main` (`434ab67...`). It cannot be treated as the
closure baseline without an explicit non-destructive synchronization decision.

### D2. Candidate commit `ae623ad` is unresolved

The object is absent from all locally available refs and objects. Any prompt,
manuscript text, or reviewer response that treats it as authoritative must be
corrected or supplied with the full external commit identifier.

### D3. The evidence-freeze control file is stale

Every checked target hash in
`outputs/revision_audit/current_evidence_freeze.json` differs from the current
tracked file:

| Frozen target | Match |
|---|---|
| Release checksum manifest | No |
| Primary workbook | No |
| Reviewer evidence map | No |
| Reviewer gap matrix | No |
| Root blocker register | No |

This historical freeze must not be overwritten. A new freeze should be created
only after the authoritative package is selected.

### D4. Manuscript source is outside the reproducible release boundary

The editable TeX source, MDPI template, inline bibliography, and figures exist
locally and have a successful build log. None is tracked in the repository,
GitHub release, or Zenodo software archive. The manuscript can be edited, but
its claims cannot yet be mechanically bound to the published evidence state.

### D5. Public status documents contradict the published state

`BLOCKERS.md`, `docs/revision/BLOCKERS.md`, `docs/revision/STATUS.md`, and the
reviewer evidence map still say that the pull request is open and that the
release/archival DOI remain future actions. The release and DOI now exist.
These are stale control statements, not scientific failures.

### D6. Reviewer statuses do not use the required classification

The current evidence map uses labels such as `Supported bounded`, `Partial`,
and generated JSON values such as `complete_bounded`. Closure requires mapping
each concern to exactly one of:

- `experimentally_evaluated`
- `analytically_addressed`
- `bounded_as_limitation`
- `pending_author_or_external_action`

### D7. Toolchain metadata contains an unresolved Circom discrepancy

Many run manifests record `environment.circom_version = 0.5.46`, while status
and methodology documents claim Circom `2.1.6`. The manifest collector invokes
`circom --version`, and some execution paths explicitly override this field to
`2.1.6`. The recorded `0.5.46` values must be explained from contemporaneous
run evidence; they must not be silently rewritten.

### D8. Direct-verifier evidence needs conservative wording

The tracked summary reports `n=30` for `verify_v2_groth16`, each using 348,811
gas, and the proof benchmark reports 30 valid proofs plus six rejected negative
cases. The public package does not contain transaction-level raw direct-verifier
receipts with transaction hashes. Until such receipts are located, use:

> Direct Solidity verification consumed 348,811 gas in each of 30 summarized
> local Hardhat verification executions.

Do not claim 30 independently archived on-chain receipts.

### D9. Release-archive SHA-256 checksums remain incomplete

GitHub does not expose checksums for its two generated source archives on the
release page. Zenodo exposes MD5
`a584f3e8967752fc2e9f81b184d17ecf`, but not SHA-256 in the record UI. Commit
identity is aligned, but exact byte-level SHA-256 verification remains pending.

## Historical evidence classification

- Normal major-revision run manifests bind environment and Git commit metadata
  and report clean trees. These may retain their recorded environments.
- `outputs/major_revision/legacy_mvp/manifests/run_manifest.json` reports a
  dirty tree. No source patch/snapshot was located in that run package; classify
  it as `dirty_tree_unreconstructable` unless an external patch is supplied.
- `outputs/revision_audit/baseline_manifest.json` also records a dirty state and
  should remain historical/regression evidence, not primary inferential evidence.
- Current machine details must not be assigned to any historical run lacking a
  contemporaneous manifest.

## Required next milestone gates

1. Choose one authoritative Git commit as the correction baseline; do not use
   the stale local checkout or unresolved `ae623ad` by implication.
2. Establish a clean, versioned manuscript source package and bind it to the
   selected evidence state.
3. Reconcile canonical control files and regenerate secondary views.
4. Create a new evidence freeze whose hashes match all targets.
5. Resolve the Circom metadata discrepancy and direct-verifier receipt wording.
6. Acquire exact GitHub/Zenodo archive bytes if SHA-256 cross-archive identity
   is required for publication closure.
7. Only then modify scientific content, rerun experiments if justified, or
   prepare a new immutable release/Zenodo version.

## Milestone decision

Stop here. Milestone 0 is complete, but the project remains `NOT_READY` for
final reviewer-response and archival closure until D1-D9 are reconciled.
