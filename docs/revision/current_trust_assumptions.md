# Current Trust Assumptions

- Local nodes are trusted to generate their metrics from the claimed data and
  model.
- The verifier process is trusted to run snarkjs correctly and sign the honest
  result.
- The authorized verifier key is trusted not to be compromised.
- Hardhat accounts and local network state are trusted.
- Kubo content addressing provides integrity for retrieved bytes, but persistent
  availability is not guaranteed by the single-node setup.
- Raw training data remain local. This is raw-data locality, not a formal
  privacy guarantee.
- The global validation set and evaluation process are trusted.
- The package assumes dependency and toolchain integrity; no supply-chain
  attestation is present.

