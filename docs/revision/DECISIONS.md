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

## D-009 Do not redistribute COMPAS raw data

The acquisition command downloads the pinned ProPublica source and records its
checksum locally. The raw CSV remains ignored because ProPublica's data terms
require attribution and restrict redistribution as a standalone data product.

## D-010 Use favorable-outcome labels consistently

Adult uses income greater than USD 50,000 as the favorable label. COMPAS uses
no two-year recidivism as the favorable label. Metric code and documentation
must retain this convention so fairness-gap directions remain interpretable.

## D-011 Exclude protected attributes from model features by default

Protected attributes are retained for group evaluation but excluded from model
features. Preprocessing is fitted on the training split only, then applied to
validation and test splits without learning new categories or statistics.

## D-012 Keep entropy diagnostic

Label, protected-group, and source entropy characterize client heterogeneity.
They are recorded for analysis but never used directly as an approval
criterion. This prevents a descriptive distribution property from becoming an
unstated fairness policy.

## D-013 Fail closed on unsatisfied minimum client size

Dirichlet allocation retries deterministically up to a configured bound. If no
partition reaches the minimum sample count for every client, the run fails and
records the error; it does not drop clients or relax the minimum silently.

## D-014 Represent undefined fairness metrics as null with reasons

Zero is a valid fairness-gap result and cannot also mean "not computable."
Missing groups, insufficient group samples, and zero rate denominators produce
`null` plus a machine-readable reason.

## D-015 Use fail-closed AND policy semantics

Every enabled metric must pass. An undefined enabled metric rejects by default,
and policy validity is bounded by an inclusive round range. Alternative
undefined behavior must be stated in the versioned policy.

## D-016 Do not substitute a heuristic for FairFed

B5 remains unavailable until the primary-paper equations, parameters, and
client-weighting behavior are reproduced and checked. Calls to B5 fail
explicitly. B0-B4, B6, and B7 remain independently implementable.

## D-017 Use strict integer canonical artifacts for V2 binding

Canonical V2 artifacts reject floating-point values. Metrics and thresholds use
scaled integers and other nonintegral values use decimal strings. SHA-256
digests map to BN254 with integer reduction modulo the scalar field.

## D-018 Keep V2 proof outcomes separate

Proof generation, Groth16 verification, artifact binding, policy evaluation,
and decision signing are independent fields. No aggregate verified flag may
hide a failed trust-boundary check.
