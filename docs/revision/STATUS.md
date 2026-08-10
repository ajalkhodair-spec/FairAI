# Major Revision Status

- Published release: `v0.3.0`
- Release commit: `6c064d0d3e01d0b6493b6650cb781379c7044fcd`
- Scope authority: reviewer reports, submitted manuscript, and
  `docs/revision/acceptance_scope.md`
- Current phase: published bounded research release and reviewer verification
- Release gate: `CLOSED_WITH_DOCUMENTED_LIMITATIONS`; see
  `docs/revision/closure_verification_status.md`
- No Azure resources or Azure results are claimed.

## Completed

- The anonymous `v0.3.0` clean-clone validation recorded 82 Python tests and 22
  Solidity tests passing from exact-pinned dependencies. The revision smoke
  scenario and real two-peer Kubo Docker Compose integration also completed.

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
- GitHub release `v0.3.0` and Zenodo version DOI
  `10.5281/zenodo.21864931` archive commit `6c064d0`.

## Preserved Failures

- The first dynamic B4 run exposed IEEE-754 precision loss for BN254 digest
  fields; decimal-string witness and ABI boundaries now have regression tests.
- The next run exposed duplicate content CIDs across rounds; metrics and proof
  artifacts now include round/node context and bind the exact published bytes.
- An IPFS concurrency review found seed overlap with sequential payloads; each
  concurrency/worker pair now has a disjoint payload namespace.

## Remaining

- Preserve BLK-005 as an explicit compiler-provenance limitation unless a
  contemporaneous Circom build transcript is recovered.
- Keep release and citation metadata synchronized for any future version.
- Azure deployment, WAN/multi-host measurements, public-chain execution, and
  consumer-outage duration remain explicitly unmeasured limitations, not
  prerequisites for the bounded local claims.

The canonical claim boundaries are in `docs/revision/current_results.md`,
`docs/revision/known_limitations.md`, and the root `BLOCKERS.md`.
