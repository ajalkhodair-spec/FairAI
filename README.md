# FairAI MVP

FairAI MVP is a tested research prototype for blockchain/IPFS-based ethical verification and auditability in federated AI workflows. It implements a small-scale, reproducible version of the FairAI framework with smart-contract approval gates, IPFS artifact traceability, verifier-mediated proof decisions, approved-only aggregation, and exported experiment results.

This repository is intended as a research artifact and framework validation MVP. It is not a security-audited production deployment.

## Scope

The implementation is intentionally scoped for reproducibility:

- local node data is generated and never published;
- each node trains a local logistic model;
- each node computes accuracy and demographic parity gap;
- a Groth16 circuit proves that public metrics meet policy thresholds;
- public metric/count signals include accuracy, fairness gap, sample counts, correct predictions, and per-group positive prediction counts;
- artifacts are published through an IPFS adapter: Kubo HTTP API, Kubo `ipfs add`, or deterministic local SHA-256 fallback;
- Kubo runs perform CID readback validation and pinning before aggregation/publication;
- `hardhat/contracts/FairAIEthicalLedger.sol` implements the ethical verification smart contract;
- `hardhat/contracts/FairAISignedVerifier.sol` verifies signed Groth16 eligibility decisions from a dedicated verifier service address;
- `hardhat/contracts/FairAIMultisigAdmin.sol` provides a 2-of-N admin executor for production-style governance;
- `hardhat/contracts/FairAIZKVerifierMock.sol` is only for deterministic fixture tests; `hardhat/contracts/FairnessEligibilityGroth16Verifier.sol` and `FairAIGroth16VerifierAdapter.sol` are retained for direct Groth16 integration work;
- the ledger uses explicit roles: admin, node operator, verifier, and aggregator;
- the contract enforces verifier-contract checks, explicit round lifecycle, duplicate-CID rejection, approval/rejection, and on-chain global model publication;
- the Python runner deploys the contract on the local Hardhat network, submits model CID records as verifier transactions, reads eligible model CIDs back from the contract, publishes the global model on-chain, and archives the round;
- the master layer retrieves only approved model CIDs and aggregates them with FedAvg;
- run outputs include a ledger, metrics CSV, global model, and report.

## What Is Validated

- Local client training with private synthetic node data.
- IPFS/Kubo artifact upload, CID readback validation, and pinning.
- Manifest/CID traceability across model, proof, public input, metrics, metadata, global model, and report artifacts.
- Smart-contract role controls, round lifecycle, duplicate rejection, approval/rejection records, eligible-model retrieval, and global model publication.
- Signed verifier-service workflow after local Groth16 verification.
- Approved-only FedAvg aggregation.
- Repeated experimental runs with CSV, spreadsheet, figure, and report outputs.
- GitHub Actions tests for Python workflow logic and Solidity contracts.

## Current Limitations

- The experiments use synthetic data and a small number of local nodes.
- The default blockchain environment is local Hardhat.
- The IPFS path is intended for local/Docker Kubo validation unless deployed with persistent pinning infrastructure.
- The result-generation workflow uses a signed verifier-service decision after local Groth16 verification; direct on-chain Groth16 verifier integration remains included for further integration work.
- The contracts and verifier flow have not received an external security audit.
- Do not use this repository as a mainnet production deployment without audit, operational monitoring, key management, persistent IPFS availability, and a full threat review.

## Quick Start

```sh
python3 -m unittest discover -s tests
cd hardhat && npm test && cd ..
python3 scripts/fairai_mvp.py --output outputs/fairai_mvp_run
```

Run with Dockerized Kubo IPFS:

```sh
./scripts/run_with_ipfs.sh outputs/fairai_mvp_run
```

This starts `ipfs/kubo` from `docker-compose.ipfs.yml` and sets:

```sh
FAIRAI_IPFS_API=http://127.0.0.1:5001
```

If Kubo is unavailable, the adapter falls back to deterministic `sha256-*` CIDs so tests and demos remain reproducible.
For production-style verification, use strict mode so fallback storage is not accepted:

```sh
FAIRAI_IPFS_API=http://127.0.0.1:5001 python3 scripts/fairai_mvp.py --output outputs/fairai_mvp_run --require-real-ipfs
```

Run repeated experiments:

```sh
FAIRAI_IPFS_API=http://127.0.0.1:5001 python3 scripts/run_experiments.py --output outputs/fairai_mvp_experiment --trials 3 --require-real-ipfs
```

This writes:

- `experiment_summary.csv`
- `experiment_summary.json`
- one full FairAI run directory per trial

Deploy contracts:

```sh
cd hardhat
npx hardhat run scripts/deploy.js --network hardhat
```

For Sepolia/testnet deployment, set:

```sh
SEPOLIA_RPC_URL=...
PRIVATE_KEY=...
npx hardhat run scripts/deploy.js --network sepolia
```

Deployment metadata is written to `hardhat/deployments/<network>.json`.

See `PRODUCTION_READINESS.md` before deploying outside a local/demo environment.

The ZK setup expects a Powers of Tau file at:

```text
zk/powersoftau_final.ptau
```

You can also point to another local setup file:

```sh
FAIRAI_PTAU_PATH=/path/to/powersoftau_final.ptau python3 scripts/fairai_mvp.py
```

## Results

Curated experiment outputs are included under `results/q1_results_package/`, including raw CSVs, figures, spreadsheet tables, report text, and LaTeX snippets.

## Citation

If you use this repository, cite it as a research software artifact. A machine-readable citation file is provided in `CITATION.cff`.

## License

This project is released under the MIT License. See `LICENSE`.
