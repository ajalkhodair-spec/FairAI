# Baseline and Ablation Methods

All methods consume the same `ClientUpdate` structure and parameter shapes.
Paired experiments must reuse the same seed, data split, partition checksum,
initial model, rounds, local epochs, optimizer, and batch size.

| Method | Eligibility | Aggregation | Infrastructure |
|---|---|---|---|
| B0 | All valid updates | Sample-weighted FedAvg | None |
| B1 | All valid updates | Sample-weighted FedAvg | Post-hoc fairness only |
| B2 | All valid updates | Sample-weighted FedAvg | Blockchain and strict IPFS |
| B3 | Public-metric policy approval | Sample-weighted FedAvg | Blockchain and strict IPFS; no Groth16 |
| B4 | Full FairAI checks | Sample-weighted FedAvg | Strict IPFS, Groth16, signed verifier, on-chain approval |
| B5 | All valid updates | FairFed (`beta=1`, signed EOD) | None; fairness-aware server aggregation |
| B6 | All valid updates | Coordinate-wise median | Adversarial comparison only |
| B7 | Full FairAI checks | Coordinate-wise median | B4 gate followed by robust aggregation |

Full FairAI eligibility requires all of: policy approval, proof verification,
artifact-binding validation, a signed decision, and on-chain approval.

Coordinate-wise median is applied independently to every scalar coordinate of
each parameter tensor. FedAvg weights each complete client update by its local
sample count.

B5 evaluates the current global model on local evaluation splits, constructs
the global EOD from sufficient counts, and applies the published stateful
FairFed weighting rule. See `docs/revision/fairfed_blocker.md` for the exact
protocol and claim boundary.

B2 fails closed unless both pinned Kubo peers are reachable. Every local model,
metrics record, metadata record, explicit proof/public `not_applicable` record,
manifest, global model, and round report is uploaded to the publisher,
retrieved and byte-checked through the consumer, and pinned there. One local
Hardhat ledger deployment records all communication rounds and verifies CID
agreement before each global publication. Its passthrough verifier is named and
documented as B2-only; it is not an ethical approval mechanism.

The method-selection and aggregation primitives are implemented and tested.
Measured multi-round B0-B7 comparisons remain part of the expanded
experiment phase and must not be inferred from unit tests.
