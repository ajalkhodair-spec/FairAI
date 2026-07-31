# Privacy Threat Analysis

| Threat | Exposure | Current control | Residual assessment |
|---|---|---|---|
| Membership inference | Model outputs and parameters | Raw examples remain local | Not formally mitigated |
| Model inversion | Serialized model and parameters | No raw dataset publication | Not formally mitigated |
| Parameter or update leakage | Local and global artifacts | Approved-only retrieval | Approval is not encryption |
| Metric leakage | Group fairness and performance values | Aggregate metrics and minimum group counts | Distribution information remains visible |
| Metadata leakage | Manifest, software, model, node, and round fields | Schemas limit fields | Published fields remain linkable |
| Timing leakage | Transactions, proof, IPFS, and training timing | Aggregate reports | Host and network observers may correlate activity |
| CID correlation | On-chain references and IPFS requests | Content integrity | Stable references enable cross-event correlation |

The analysis is qualitative and scoped to exposures created by this
implementation. No privacy-attack success rate is reported.
