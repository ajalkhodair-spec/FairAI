# Signed Verifier V2 Trust Model

## Security Boundary

`FairAISignedVerifierV2` is a versioned EIP-712 decision verifier. The legacy
signed verifier remains unchanged for regression.

The signed `Decision` binds:

- node ID;
- round ID;
- packed policy version;
- manifest hash;
- metrics hash;
- signer-specific nonce;
- proof-verification result;
- policy result;
- final decision;
- expiration.

The EIP-712 domain additionally binds chain ID and verifying-contract address.

## On-Chain Controls

- owner-managed authorized-signer registry;
- signer revocation;
- signer-specific nonce consumption;
- decision-digest consumption;
- expiration enforcement;
- lower-half `s` and valid-`v` ECDSA checks;
- explicit node/round public-signal checks in the compatibility adapter.

Exact replay fails by used digest. A different decision with a reused signer
nonce fails by used nonce. Signatures produced for another chain or verifier
contract recover to an unauthorized address.

## Compromised Signer

The reproducible Solidity test
`demonstrates the authorized-key compromise trust limitation` signs fabricated
passing hashes with an authorized key. The contract accepts the decision.

This is expected: signature validity proves authorization, not signer honesty.
Revocation limits future use after compromise is detected but cannot identify
false decisions already signed by an authorized key.

## Operational Requirements

- keep signer keys outside application source and repository history;
- use hardware-backed or managed signing where possible;
- monitor `DecisionConsumed` and signer-administration events;
- rotate and revoke signers under documented incident procedures;
- use short expirations and monotonic nonce allocation;
- do not treat a signed decision as proof of metric correctness.

A 2-of-3 committee remains a stretch goal and is not claimed.
