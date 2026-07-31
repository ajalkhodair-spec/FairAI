# Known Limitations

- Direct V2 Groth16 generation and on-chain pairing verification are blocked by
  the unavailable pinned Circom 2.1.6 artifacts.
- Two-peer Kubo overhead, outage, recovery, and concurrency are not measured in
  the frozen evidence package because Docker socket access was denied.
- FairFed is not implemented; no heuristic is substituted under that name.
- Real-data experiments use Adult and COMPAS binary classification and one
  primary protected attribute per dataset.
- The small MLP shows substantial seed sensitivity in the five-seed suite.
- Poisoning experiments cover random weights, sign flip factor `-1`, and binary
  label flipping at a 20% malicious-client ratio.
- Coordinate median is evaluated as robust aggregation, not as proof that
  poisoning is detected.
- The signed verifier remains a trust point; a compromised authorized key can
  submit an accepted false decision.
- Fairness values are supplied to the proof relation. Correct derivation from
  private data is not independently proved.
- Raw-data locality is not differential privacy or secure aggregation.
- Hardhat gas is measured; public-chain fiat costs are modeled assumptions.
- Contracts and cryptographic integration have not received an external audit.
- Anonymous public repository accessibility and remote clean-clone validation
  remain blocked.

See `BLOCKERS.md` for exact resolutions.
