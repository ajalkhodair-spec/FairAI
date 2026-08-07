# Known Undetected Threats

1. A threshold-compliant supplied metric can satisfy the current proof relation
   even when it was not correctly derived from private data. The circuit binds
   values and applies threshold constraints; it does not recompute training or
   fairness metrics from private records.
2. A compromised authorized verifier can sign and submit a false decision. The
   single-verifier contract authenticates the signer, not the signer's honesty.
3. Poisoned updates that remain numerically valid and satisfy the measured
   policy are not necessarily detected. Robust aggregation limits some update
   influence but is not a poisoning detector.
4. IPFS content addressing detects changed bytes under a different CID or
   digest, but it does not guarantee persistence or availability.
5. Administrator, dependency, endpoint, and local-host compromise are not
   eliminated by the current contracts.

These limitations constrain the implementation's security claims even where
the enforcement tests pass.
