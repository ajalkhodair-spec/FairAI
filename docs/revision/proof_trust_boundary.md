# V2 Proof Trust Boundary

The client prepares scaled metrics, canonical artifacts, public inputs, and a
Groth16 proof. The verifier service must not trust the client's digest fields or
policy result.

The verifier service:

1. loads and canonicalizes the manifest;
2. recomputes its SHA-256 digest and BN254 field mapping;
3. loads and canonicalizes the metrics artifact;
4. recomputes its SHA-256 digest and BN254 field mapping;
5. compares all metrics, thresholds, mask values, node ID, round ID, packed
   policy version, nonce, and digest fields with public inputs;
6. verifies the Groth16 proof;
7. independently evaluates the versioned policy;
8. signs a full decision payload only if the configured decision rules allow.

Outputs remain separate:

- `proof_generated`;
- `proof_verified`;
- `artifact_binding_valid`;
- `policy_passed`;
- `decision_signed`.

No aggregate `verified=true` field may hide which step failed.
