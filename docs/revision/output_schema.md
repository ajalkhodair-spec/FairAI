# Revision Output Schema

Each run directory contains:

| Directory | Purpose |
|---|---|
| `config/` | Canonical resolved configuration |
| `environment/` | Environment details and future dependency exports |
| `raw/` | Direct measured records |
| `derived/` | Deterministic summaries derived from raw evidence |
| `logs/` | Execution and failure logs |
| `datasets/` | Dataset provenance, checksums, and preparation records |
| `partitions/` | Client partition assignments and checksums |
| `models/` | Serialized local and global models |
| `metrics/` | Local and global metric records |
| `proofs/` | Proof inputs, proofs, and verification records |
| `ipfs/` | CID, add, pin, retrieval, and availability evidence |
| `blockchain/` | Addresses, receipts, events, gas, and lifecycle state |
| `attacks/` | Attack inputs and observed outcomes |
| `statistics/` | Descriptive and inferential statistics |
| `reports/` | Scenario-level human-readable reports |
| `manifests/` | Versioned run manifest |

Missing measurements remain `null` and are listed in `missing_fields`. Estimated
values must use `evidence_type = estimated`.

