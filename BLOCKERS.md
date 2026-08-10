# Blocker Register

| ID | Status | Scope | Exact blocker or resolution | Scientific effect / next step |
|---|---|---|---|---|
| BLK-001 | Resolved bounded | V2 Groth16 | The checksum-manifested phase-2 Powers of Tau, R1CS, ZKey, VKey, real proof, generated Solidity verifier, composite verifier, and negative suite pass. The artifact manifest declares Circom 2.1.6; compiler-version provenance is tracked separately in BLK-005. | Thirty valid proof repetitions and six rejection cases are measured. A multi-party phase-2 ceremony remains required before production deployment. |
| BLK-002 | Resolved bounded | Two-peer IPFS | Two native Kubo 0.29.0 peers completed 30-repeat add/pin/cold/warm/concurrency measurements, 30 publisher outage/recovery trials, and strict B2/B4/B7 runs at 5/10 clients. A clean public clone also completed the short two-peer Docker Compose integration protocol. | Consumer outage, WAN, and multi-host measurements remain limitations rather than completed evidence. The Compose run is functional evidence, not a replacement for the 30-repeat performance archive. |
| BLK-003 | Resolved | FairFed | The published stateful server weighting rule, signed EOD sufficient-statistic calculation, beta-zero equivalence, accuracy fallback, deterministic tests, and paired Adult/COMPAS runs are complete. | Report the observed accuracy-fairness trade-off; do not claim reproduction of every local debiasing variant. |
| BLK-004 | Resolved | Public repository | Pull request `#2` was merged, GitHub release `v0.3.0` points to commit `6c064d0d3e01d0b6493b6650cb781379c7044fcd`, and Zenodo version DOI `10.5281/zenodo.21864931` archives the release. An anonymous depth-one clone of tag `v0.3.0` passed 82 Python and 22 contract tests, the revision smoke scenario, and a real two-peer Kubo Docker Compose integration run. | Public access, clean-clone installation, release publication, archival DOI assignment, core tests, and functional IPFS execution are verified. Full legacy regeneration additionally requires the documented external Powers of Tau file and ZK toolchain. |
| BLK-005 | Open | V2 compiler provenance | The V2 artifact manifest declares Circom 2.1.6, while many historical run manifests and the current executable report 0.5.46. No contemporaneous compiler build transcript was located in the public package. | Do not claim that every run used or regenerated artifacts with Circom 2.1.6. Resolve with contemporaneous evidence or describe the artifact-manifest declaration and historical environment values separately. |

The original four revision blockers are resolved within their stated bounds.
BLK-005 remains open as a publication-provenance blocker.
Unmeasured recovery, multi-host, and public-chain scenarios remain labeled
limitations rather than completed evidence.

Publication closure discrepancies are tracked separately in
`audits/prechange/evidence_discrepancy_report.md`; they do not retroactively
change the bounded experimental results recorded here.
