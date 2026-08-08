# Known Limitations

- The V2 artifact manifest declares Circom 2.1.6. Historical manifests and the
  closure environment report 0.5.46, and no contemporaneous compiler transcript
  was archived. The verified phase-2 Powers of Tau, generated Groth16 artifacts,
  and direct pairing-verifier tests remain usable evidence, but compiler-build
  provenance is unresolved. The experimental phase-2 ZKey has one contributor
  and is not a production ceremony artifact.
- Two native local Kubo 0.29.0 peers provide measured add, pin, cold/warm
  retrieval, concurrency, publisher outage availability, and restart recovery.
  Consumer outage, WAN behavior, and multi-host Kubo performance are not
  measured.
- FairFed implements the published server weighting rule and is reference-tested.
  This does not claim implementation of every client-side debiasing variant used
  by fair-federated-learning literature.
- Real-data experiments use Adult and COMPAS binary classification and one
  primary protected attribute per dataset.
- The bounded Adult small-MLP matrix covers B0, B3, and B5 under IID and
  Dirichlet 0.3 for five paired seeds. It shows substantial seed sensitivity
  and no comparison remains significant after Holm correction.
- Poisoning experiments cover random weights, sign flip factor `-1`, and binary
  label flipping at a 20% malicious-client ratio.
- Coordinate median is evaluated as robust aggregation, not as proof that
  poisoning is detected.
- The V2 fairness gate rejected most tested label-flip updates but accepted all
  tested sign-flip updates and some or all random-weight updates. It proves the
  configured metric relation, not update provenance or poisoning absence.
- The signed verifier remains a trust point; a compromised authorized key can
  submit an accepted false decision.
- The full-path false-metric experiment demonstrates that fabricated passing
  values can be proved, stored, signed, approved, retrieved, and aggregated.
  Correct metric derivation from private data is not independently proved.
- Raw-data locality is not differential privacy or secure aggregation.
- Hardhat gas is measured; public-chain fiat costs are modeled assumptions.
- Contracts and cryptographic integration have not received an external audit.
- Public repository accessibility and clean-clone validation are complete.
  Measured Azure multi-host execution remains pending.

See `BLOCKERS.md` for exact resolutions.
