# Major Revision Decisions

## D-001 Preserve the existing implementation

The current three-node synthetic logistic-regression path remains the Version 1
regression scenario. Revision work will be additive and versioned.

## D-002 Treat strict IPFS separately

The existing adapter supports a deterministic local fallback. That fallback is
useful for unit tests but is not admissible as IPFS evidence. All IPFS-dependent
revision scenarios will require real Kubo and fail explicitly otherwise.

## D-003 Describe current proof semantics narrowly

The current Groth16 circuit proves threshold relations over supplied public
scaled metrics plus node and round values. It does not prove correct metric
computation, dataset authenticity, honest training, or model integrity.

## D-004 Do not infer GitHub publication

The local checkout has no commit or remote, the expected URL returned 404, and
the CLI credential is invalid. Public accessibility remains unverified until an
anonymous request succeeds.

## D-005 Do not tag an uncommitted tree

`v1.0.0-submitted` cannot be created meaningfully until the submitted baseline
is represented by a commit. The closest-state decision must be documented first.

Resolution: the original staged 72-file tree was tested, committed as
`e34338c1b5148768aef948d28ae52896220c5414`, and tagged
`v1.0.0-submitted`. The absence of earlier history remains documented.

## D-006 Reuse verified local cryptographic artifacts only for diagnosis

The clean repository intentionally excludes proving artifacts. Existing local
R1CS, WASM, ZKey, verification key, and Powers of Tau files were used for the
diagnostic legacy reproduction only after `snarkjs zkv` reported `ZKey Ok`.
Their hashes are recorded in the audit manifest. They remain untracked.

## D-007 Use JSON-compatible YAML in G1

Revision configuration files use JSON syntax with `.yaml` extensions. JSON is a
valid YAML subset, allowing clean-clone configuration loading with the Python
standard library. This avoids introducing an unneeded parser dependency before
the scientific stack is pinned in the real-data phase.

## D-008 Preserve explicit planned executors

All required scenario configurations exist, but scenarios not yet implemented
use `executor: planned`. Attempting to run one creates a failed manifest and
raises `NotImplementedError`; it cannot silently emit placeholder results.
