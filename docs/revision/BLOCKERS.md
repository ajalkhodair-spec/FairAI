# Major Revision Blockers

## B-005 Faithful FairFed baseline

- Status: open
- Impact: B5 comparative rows cannot be generated.
- Evidence: `docs/revision/fairfed_blocker.md`
- Resolution gate: primary-paper equations, parameter mapping, reference trace,
  and manually verifiable weighting tests.

## B-001 Missing Git baseline

The inspected checkout initially reported `No commits yet on main` and had no
remote. The staged tree has now been frozen as the closest verified state and
tagged `v1.0.0-submitted`.

Remaining gap: no older history exists to prove that this tree is byte-for-byte
the state used for the manuscript submission.

## B-002 Public repository is not anonymously resolvable

`https://github.com/ajalkhodair-spec/FairAI-MVP` returned 404 from an anonymous
check. This can mean the repository is private, absent, or named differently.

Smallest valid resolution: confirm the exact repository URL and make it public
manually if publication is intended. Visibility will not be changed
automatically.

## B-003 GitHub CLI authentication

`gh auth status` reports an invalid token for `ajalkhodair-spec`.

Smallest valid resolution: run `gh auth refresh -h github.com` before any
authenticated push or release operation.

## B-004 ZK toolchain compatibility

The available `circom --version` is 0.5.46, while regeneration requires a
compatible Circom 2 binary. The Powers of Tau file is also absent by design.

Existing compiled artifacts were cryptographically verified and allowed the
diagnostic legacy run to complete. Phase 1 still requires a pinned Circom 2
toolchain and documented Powers of Tau acquisition/checksum for clean
reproduction.
