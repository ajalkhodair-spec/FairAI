# Current Reproducibility Gaps

Historical note: this file records the gaps identified before the major-revision
work. It is not the current release status. See `BLOCKERS.md` and
`docs/revision/STATUS.md` for the reconciled state.

- No committed Git baseline or configured remote in the inspected checkout.
- Expected public repository URL is not anonymously resolvable.
- No unified YAML configuration runner.
- No versioned run-manifest schema or validation.
- Python runtime dependencies are not locked for the experiment implementation.
- Circom version is not pinned and the local binary appears incompatible.
- Powers of Tau acquisition and checksum are not automated.
- Existing repetitions reuse identical deterministic data and seeds.
- Output directories are deleted at run start, so runs are not resumable or
  interrupt-safe.
- Strict Kubo is optional and the README describes fallback behavior.
- Kubo benchmark has one node and no cold/warm/recovery isolation.
- No Adult or COMPAS checksum, preprocessing, or license documentation.
- No clean-clone reproduction record.
- No test covers configuration hashes, environment capture, or result schemas.
