# Major Revision Status

- Active branch: `major-revision-closure`
- Reconciliation baseline: public `main` commit
  `434ab67f067c8ab26f1908369f62d2e2b4ec3fe3`
- Scope authority: reviewer reports, submitted manuscript, and
  `docs/revision/acceptance_scope.md`
- Current phase: evidence/manuscript reconciliation and immutable release
  preparation
- Release gate: `VALIDATION_PENDING_ENVIRONMENT`; see
  `docs/revision/closure_verification_status.md`
- No Azure resources or Azure results are claimed.

## Completed

- The published clean-clone validation recorded 77 Python tests and 22 Solidity
  tests passing. Milestone 1 verification must rerun these suites after the
  reconciliation changes.

- Adult and COMPAS loaders, logistic regression and small MLP, IID and
  Dirichlet partitions, multi-round execution, and group-fairness policies.
- B0-B7 implementation, including measured FairFed Adult/COMPAS comparisons and
  algorithmic scaling to 50 logical clients.
- Checksum-manifested V2 artifacts that declare Circom 2.1.6, 30 valid proofs,
  six negative cases, direct
  Solidity pairing verification, EIP-712 binding, and a 30-execution local
  Hardhat gas summary. Transaction-level direct-verifier receipt hashes are not
  part of the public evidence package.
- Two native Kubo 0.29.0 peers with 30-repeat upload, cold/warm retrieval, and
  concurrency measurements over 1 KiB through 10 MiB payloads.
- Strict B2/B4/B7 execution at 5 and 10 clients, three seeds and three rounds:
  18 contract executions, 54 archived rounds, 2,688 verified retrievals, 258
  proof decisions, and 387 ledger records.
- Targeted B4/B7 poisoning execution with four attack conditions, three seeds,
  and three rounds: 24 contract executions, 72 rounds, 2,664 verified
  retrievals, 360 proof decisions, and 360 ledger records.
- Bicep compilation and shell validation for the bounded three-host Azure
  topology; no deployment was performed.
- GitHub release `v0.2.1` and Zenodo version DOI
  `10.5281/zenodo.21838695` archive commit `cabcea6`.

## Preserved Failures

- The first dynamic B4 run exposed IEEE-754 precision loss for BN254 digest
  fields; decimal-string witness and ABI boundaries now have regression tests.
- The next run exposed duplicate content CIDs across rounds; metrics and proof
  artifacts now include round/node context and bind the exact published bytes.
- An IPFS concurrency review found seed overlap with sequential payloads; each
  concurrency/worker pair now has a disjoint payload namespace.

## Remaining

- Bind the editable manuscript source to the reconciled evidence state.
- Create a new evidence freeze with hashes matching every canonical target.
- Reconcile historical Circom version metadata without altering run manifests.
- Rebuild the manuscript and rerun clean-clone validation.
- Publish a new immutable release and Zenodo version if any supporting artifact
  differs from `v0.2.1`.
- Azure deployment, WAN/multi-host measurements, public-chain execution, and
  consumer-outage duration remain explicitly unmeasured limitations, not
  prerequisites for the bounded local claims.

The canonical claim boundaries are in `docs/revision/current_results.md`,
`docs/revision/known_limitations.md`, and the root `BLOCKERS.md`.
