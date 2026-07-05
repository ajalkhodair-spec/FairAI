# FairAI Final MVP Results Interpretation

The final MVP validates the FairAI governance workflow at small scale. It demonstrates privacy-preserving local training, strict Kubo/IPFS artifact publication, CID-based traceability, on-chain CID registration, proof-based ethical verification through a signed verifier-service path, smart-contract approval/rejection, approved-only weighted FedAvg, global model publication, and lifecycle monitoring.

Node 3 was rejected because its demographic parity gap exceeded the configured eligibility threshold. This rejection is the central policy-gate result: FairAI does not claim to solve fairness globally, but it enforces the configured fairness eligibility policy before aggregation.

Approved-only aggregation was completed with Node 1 and Node 2. Node 3 was excluded, so the global model was built only from local model artifacts that passed the approval gate.

Strict IPFS mode was used through Dockerized Kubo. The final run recorded Kubo HTTP mode, retrieval validation, and pin checks for the tracked CIDs. This supports artifact traceability and repeatable audit inspection.

The experiment generates Groth16 proofs using the FairnessEligibility.circom circuit and verifies them locally with snarkjs. For the on-chain approval path, the final MVP uses a signed verifier-service model: the verifier checks the proof off-chain, signs the verification decision, FairAISignedVerifier verifies the authorized signer and decision on-chain, and FairAIEthicalLedger records the model as approved or rejected.

Across three repeated trials, the framework metrics were stable: the approval rate remained two of three nodes, the global model metrics were consistent, and timing/gas results were exported for reporting. These values should be interpreted as MVP workflow measurements, not as production throughput benchmarks.

## Limitations

- The experiment is a small-scale MVP with three local nodes.
- The local datasets are synthetic.
- The model workload is logistic regression.
- The blockchain network is local Hardhat, not a public or consortium deployment.
- Direct Solidity Groth16 verification was not used as the final decision path.
- The final on-chain approval uses a signed verifier-service path.
- The results validate the framework path rather than production throughput.
