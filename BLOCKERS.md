# Blocker Register

| ID | Status | Scope | Exact blocker or resolution | Scientific effect / next step |
|---|---|---|---|---|
| BLK-001 | Resolved | V2 Groth16 | Circom 2.1.6 was built from tag `v2.1.6`; the verified phase-2 Powers of Tau, R1CS, ZKey, VKey, real proof, generated Solidity verifier, composite verifier, and negative suite all pass. | Thirty valid proof repetitions and six rejection cases are measured. A multi-party phase-2 ceremony remains required before production deployment. |
| BLK-002 | Resolved bounded | Two-peer IPFS | Two native Kubo 0.29.0 peers completed 30-repeat add/pin/cold/warm/concurrency measurements, 30 publisher outage/recovery trials, and strict B2/B4/B7 runs at 5/10 clients. | Consumer outage, WAN, Docker Compose, and multi-host measurements remain limitations rather than completed evidence. |
| BLK-003 | Resolved | FairFed | The published stateful server weighting rule, signed EOD sufficient-statistic calculation, beta-zero equivalence, accuracy fallback, deterministic tests, and paired Adult/COMPAS runs are complete. | Report the observed accuracy-fairness trade-off; do not claim reproduction of every local debiasing variant. |
| BLK-004 | Active | Public release | The local repository has no configured remote and anonymous repository access has not been verified. | Public citation and clean-clone-from-GitHub evidence remain unavailable. Configure the public remote, push, and run the anonymous clean-clone protocol. |

Independent experiment, security, gas, statistics, privacy, ethics, and
reporting work continues while BLK-004 remains open. Unmeasured recovery,
multi-host, and public-chain scenarios remain labeled missing.
