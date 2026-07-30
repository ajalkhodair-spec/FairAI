# Phase 0 Repository Audit

## Classification

| Area | Classification | Evidence |
|---|---|---|
| Python orchestration | Implemented | `scripts/fairai_mvp.py` |
| Synthetic data | Implemented and deterministic | Fixed per-node and validation seeds |
| Logistic regression | Implemented | In-house batch gradient descent |
| Real datasets | Missing | No Adult or COMPAS loader |
| MLP | Missing | No common model interface |
| Group fairness | Partially implemented | DP and EO use protected groups; undefined groups become zero |
| Policy engine | Partially implemented | Fixed accuracy and DP thresholds |
| Aggregation | Implemented | Weighted FedAvg for three parameters |
| Robust aggregation | Missing | No median or trimmed mean |
| Baselines | Missing | No B0-B5 experiment interface |
| Legacy Groth16 circuit | Implemented source; execution pending | Threshold relation over supplied metrics |
| Direct Solidity Groth16 | Partially integrated | Generated verifier and adapter exist; default runner uses signed path |
| Signed verifier | Implemented but weakly bound | Personal-sign style payload, immutable single signer |
| Replay protection | Missing | No nonce, expiry, chain ID, round/policy digest registry |
| Ledger lifecycle | Implemented | Open through Archived states |
| Roles | Implemented locally | Custom role mapping |
| Duplicate protection | Implemented | Submission and CID checks |
| Kubo integration | Implemented with fallback | HTTP/CLI adapter and single-node Compose |
| Strict IPFS | Implemented at runner boundary | `--require-real-ipfs` |
| Two-peer IPFS benchmark | Missing | Single Kubo service only |
| Unit tests | Implemented but narrow | Python and Hardhat tests |
| Revision manifests and schemas | Missing before this audit | Existing Q1 manifest is result-package specific |
| Public Git history | Broken in inspected checkout | No commits and no remote |

## Important Findings

1. The default pipeline determines expected eligibility from local proof results
   before the contract call, retrieves those models, and aggregates them. It then
   checks that the contract returns the same CID set. This validates consistency,
   but the aggregation input is not first obtained from an independently queried
   on-chain approval set.
2. The signed verifier runner signs the same Boolean supplied by the local
   process. A compromised authorized signer remains a trusted decision oracle.
3. IPFS HTTP failures may fall through to the local content-addressed copy unless
   strict mode rejects the adapter mode at startup. Mid-run HTTP read failure can
   still read the local mirror, so availability evidence needs a stricter V2
   boundary.
4. Existing timing evidence is limited and does not distinguish cold and warm
   retrieval.
5. Existing Q1 evidence is curated, but it lacks commit/configuration/environment
   traceability required for the revision.

## Targeted Validation

- Python unit/integration tests: 4 passed.
- Solidity tests: 8 passed.
- Solidity compilation: 6 files compiled.
- npm production dependency audit: no production vulnerabilities reported.
- Legacy ZKey: verified against the R1CS and recorded Powers of Tau.
- Strict Kubo diagnostic reproduction: 3 trials completed.
- Numeric model and policy results: matched the submitted values.
- Global publication gas: matched at `449664`.
- Timing values: observed afresh and not expected to match exactly.
