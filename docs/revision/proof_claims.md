# V2 Proof Claims

When generated with the versioned V2 circuit and verified against the matching
verification key, a valid proof claims:

1. supplied scaled accuracy and enabled scaled fairness gaps satisfy their
   supplied threshold relations;
2. every enabled-metric mask bit is binary;
3. metric values and thresholds fit the configured 32-bit range;
4. node ID, round ID, packed policy version, and nonce fit 64 bits;
5. the proof exposes the supplied manifest and metrics digest field elements.

The off-circuit verifier separately recomputes canonical artifact hashes,
checks all public metric, threshold, mask, identity, round, policy, nonce, and
digest values, and independently evaluates the selected policy.

The V2 source is separate from the preserved Version 1 circuit.
