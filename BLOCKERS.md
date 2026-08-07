# Blocker Register

| ID | Status | Scope | Exact blocker or resolution | Scientific effect / next step |
|---|---|---|---|---|
| BLK-001 | Resolved | V2 Groth16 | Circom 2.1.6 was built from tag `v2.1.6`; the verified phase-2 Powers of Tau, R1CS, ZKey, VKey, real proof, generated Solidity verifier, composite verifier, and negative suite all pass. | Thirty valid proof repetitions and six rejection cases are measured. A multi-party phase-2 ceremony remains required before production deployment. |
| BLK-002 | Resolved bounded | Two-peer IPFS | Two native Kubo 0.29.0 peers completed 30-repeat add/pin/cold/warm/concurrency measurements, 30 publisher outage/recovery trials, and strict B2/B4/B7 runs at 5/10 clients. | Consumer outage, WAN, Docker Compose, and multi-host measurements remain limitations rather than completed evidence. |
| BLK-003 | Resolved | FairFed | The published stateful server weighting rule, signed EOD sufficient-statistic calculation, beta-zero equivalence, accuracy fallback, deterministic tests, and paired Adult/COMPAS runs are complete. | Report the observed accuracy-fairness trade-off; do not claim reproduction of every local debiasing variant. |
| BLK-004 | Resolved | Public repository | The revision branch is publicly available at `https://github.com/ajalkhodair-spec/FairAI`, pull request `#1` is open, GitHub Actions run `31160131439` passed, and an anonymous depth-one clone of commit `d131023df6ab9002b8244474ef1f03a9453aee2b` passed 77 Python and 22 contract tests. | Anonymous access and clean-clone reproduction are verified. A versioned GitHub release and archival DOI remain publication actions after review and merge. |

All four tracked revision blockers are resolved within their stated bounds.
Unmeasured recovery, multi-host, and public-chain scenarios remain labeled
limitations rather than completed evidence.
