# Reproducibility Infrastructure

Revision experiments use JSON-compatible YAML configurations under
`configs/revision/`. The dependency-free loader canonicalizes each configuration
and records its SHA-256 hash.

Every run creates the standard evidence directory structure under
`outputs/major_revision/<run_id>/` and writes:

- the resolved configuration;
- a versioned run manifest;
- raw and derived outputs;
- explicit logs on failure.

Runs use fixed seeds. `--resume` returns a completed run only when the stored
configuration hash matches. A different configuration cannot reuse the same run
directory.

The legacy runner remains available. Strict IPFS evidence requires
`--require-real-ipfs` in its configuration and a reachable Kubo endpoint.

## Smoke Test

```sh
make revision-smoke
```

The smoke scenario validates configuration loading, deterministic training,
output creation, hashing, manifest generation, and resume behavior. It does not
claim to validate blockchain, IPFS, or Groth16.

The current CI circuit check validates the expected legacy source bindings and
threshold constraints. Full circuit regeneration remains blocked until the
clean environment pins a compatible Circom 2 binary and obtains the documented
Powers of Tau artifact.
