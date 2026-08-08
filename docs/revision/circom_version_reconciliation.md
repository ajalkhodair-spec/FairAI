# Circom Version Reconciliation

The V2 artifact manifest declares Circom `2.1.6`, snarkjs `0.7.5`, circuit and
artifact hashes, 751 constraints, and successful artifact verification. The
declaration identifies the intended artifact-build toolchain but is not, by
itself, a contemporaneous compiler execution transcript.

Several historical run manifests record `environment.circom_version = 0.5.46`,
and the executable available during closure verification also reports `0.5.46`.
Those values were captured by invoking the `circom` executable available in the
run environment. Other execution paths explicitly set `2.1.6` after checking
the pinned V2 toolchain. The conflicting historical values must remain intact;
they cannot be retroactively replaced with the current or intended compiler.

Claim boundary:

- state that the artifact manifest declares `2.1.6`; do not present that
  declaration as independently reconstructed build provenance;
- retain `0.5.46` when reporting a historical manifest that recorded it;
- do not imply that every experiment regenerated the V2 artifacts;
- do not assign current machine metadata to historical runs.

The discrepancy is unresolved provenance debt. It neither proves that the
tracked verifier was generated with `0.5.46` nor independently proves the
manifest's `2.1.6` declaration.
