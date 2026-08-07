# Privacy Scope

“FairAI keeps raw training data local. The current implementation does not
provide a formal guarantee against membership inference, model inversion,
model-update leakage, or metadata leakage.”

Raw records are processed by each local client and are not intentionally
uploaded to IPFS or written on-chain. This locality reduces direct raw-data
movement, but serialized models, parameters, metrics, public proof inputs,
manifests, CIDs, transaction senders, events, gas, and timing remain observable
to different parties.

The implementation does not add differential privacy, encrypted aggregation,
trusted execution, private information retrieval, anonymous credentials, or
formal traffic-analysis resistance. Zero knowledge applies to the configured
proof witness and statement; it does not make model parameters or workflow
metadata confidential.

The field-level boundary is recorded in
`outputs/major_revision/governance/privacy_exposure_inventory.csv`.
