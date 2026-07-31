# Public and Permissioned Chain Implications

The measured blockchain evidence uses an ephemeral local Hardhat
Ethereum-compatible chain. It measures contract gas, local transaction latency,
failure behavior, and local sequential/concurrent submission throughput under a
fixed compiler and bytecode. It does not measure public-chain congestion,
confirmation finality, reorganization risk, validator diversity, or fee
volatility.

Public-chain monetary values are illustrative estimates computed from measured
gas and explicitly configured gas-price and native-token-price assumptions. No
live market price is fetched. These estimates should be presented separately
from measured Hardhat values.

A permissioned deployment could provide controlled validator membership,
predictable fees, privacy-aware network access, and lower confirmation
variance. It also introduces consortium governance, validator collusion,
availability, key management, and weaker public verifiability assumptions.
Those implications are analytical; this revision does not run a permissioned
consensus network.

The generated evidence therefore uses three labels:

- `measured_hardhat`: local execution on the pinned Hardhat environment;
- `modeled`: arithmetic cost scenarios using explicit assumptions;
- `analytical`: implications not executed as a network experiment.
