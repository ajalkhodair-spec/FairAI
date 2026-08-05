# Major Revision Status

- Active branch: `major-revision-azure`
- Scope authority: reviewer reports, submitted manuscript, and
  `docs/revision/acceptance_scope.md`
- Current phase: measured-evidence freeze followed by Azure execution and public
  clean-clone validation
- No Azure resources or Azure results are claimed.

## Completed

- Full local regression suite: 69 Python tests and 20 Solidity tests pass.

- Adult and COMPAS loaders, logistic regression and small MLP, IID and
  Dirichlet partitions, multi-round execution, and group-fairness policies.
- B0-B7 implementation, including measured FairFed Adult/COMPAS comparisons and
  algorithmic scaling to 50 logical clients.
- Pinned Circom 2.1.6 V2 artifacts, 30 valid proofs, six negative cases, direct
  Solidity pairing verification, EIP-712 binding, and 30 gas receipts.
- Two native Kubo 0.29.0 peers with 30-repeat upload, cold/warm retrieval, and
  concurrency measurements over 1 KiB through 10 MiB payloads.
- Strict B2/B4/B7 execution at 5 and 10 clients, three seeds and three rounds:
  18 contract executions, 54 archived rounds, 2,688 verified retrievals, 258
  proof decisions, and 387 ledger records.
- Bicep compilation and shell validation for the bounded three-host Azure
  topology; no deployment was performed.
- 68 Python and 20 Solidity tests pass; Bicep compilation and Azure shell syntax
  validation also pass.

## Preserved Failures

- The first dynamic B4 run exposed IEEE-754 precision loss for BN254 digest
  fields; decimal-string witness and ABI boundaries now have regression tests.
- The next run exposed duplicate content CIDs across rounds; metrics and proof
  artifacts now include round/node context and bind the exact published bytes.
- An IPFS concurrency review found seed overlap with sequential payloads; each
  concurrency/worker pair now has a disjoint payload namespace.

## Remaining

- Deploy and measure the Azure 5/10/20-client matrix, then destroy resources.
- Measure consumer outage, WAN/multi-host behavior, and Azure cost.
- Run targeted B4/B7 poisoning comparisons.
- Configure and verify the public remote, anonymous clean clone, and release.

The canonical claim boundaries are in `docs/revision/current_results.md`,
`docs/revision/known_limitations.md`, and the root `BLOCKERS.md`.
