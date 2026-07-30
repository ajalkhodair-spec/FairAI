# Current Proof Semantics

The legacy `FairnessEligibility.circom` circuit exposes scaled accuracy,
demographic-parity gap, minimum accuracy, maximum gap, node ID, and round ID.
It constrains:

- `accuracy >= minimum accuracy`
- `demographic-parity gap <= maximum gap`

The proof therefore establishes threshold satisfaction for supplied values
under the circuit relation.

It does not establish that:

- metrics were computed correctly from private data;
- metrics correspond to the submitted model;
- data are authentic;
- training was honest;
- the model is not poisoned;
- the protected attribute is correct.

The current signed on-chain path verifies an authorized signature over the
verifier-contract address, public-signal hash, and approval Boolean. It does not
provide EIP-712 domain separation, nonce tracking, expiry, policy-version
binding, or artifact-digest binding.

