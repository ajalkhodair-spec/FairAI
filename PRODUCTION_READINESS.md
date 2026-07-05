# Production Readiness and Public-Use Scope

This repository is a production-structured research MVP, not a production-certified system. It demonstrates the main FairAI operations at small scale and includes automated tests, but it has not been externally audited and should not be deployed to a public production network without additional engineering and security review.

Use the repository publicly as:

- a research prototype;
- a framework validation artifact;
- a reproducible small-scale MVP;
- a starting point for production engineering.

Do not describe the current repository as a fully production-ready FairAI deployment.

## Implemented Hardening

- Smart contract stores only CIDs and status metadata, not raw data or model payloads.
- Explicit role controls:
  - `ADMIN_ROLE`
  - `NODE_OPERATOR_ROLE`
  - `VERIFIER_ROLE`
  - `AGGREGATOR_ROLE`
- Zero-address role assignments are rejected.
- Verifier address must be a deployed contract.
- The final admin cannot be revoked.
- A deployable 2-of-N multisig admin executor is included for admin operations.
- Rounds have explicit lifecycle states.
- Late submissions are rejected after submission close.
- Duplicate node/round submissions are rejected.
- Reused artifact CIDs are rejected.
- Global publication requires aggregation state and approved participant model CIDs.
- IPFS/Kubo runs validate and pin manifest, model, report, and global model CIDs.
- Strict IPFS mode is available with `--require-real-ipfs`.
- Deployment metadata is written under `hardhat/deployments/`.
- Repeated experiments export CSV and JSON summaries.

## Verifier Modes

The result-generation runner uses `FairAISignedVerifier`, which verifies a signature from a dedicated verifier service address. The service decision is produced after local Groth16 verification with snarkjs.

The local test suite can use `FairAIZKVerifierMock` as a deterministic verifier adapter for fixture-only tests.

The project also exports `FairnessEligibilityGroth16Verifier.sol` from the Circom/snarkjs proving key. For a non-demo deployment, use the generated Groth16 verifier or deploy an adapter that:

1. Decodes proof calldata into Groth16 proof arrays.
2. Decodes public signals into the generated verifier's expected fixed-size array.
3. Calls `Groth16Verifier.verifyProof(...)`.
4. Exposes the common `IFairAIVerifier.verifyProof(bytes,uint256[])` interface expected by the ledger.

Do not deploy the deterministic mock verifier to a public production network as the final security verifier.

The direct Groth16 adapter is included for integration work, but the final generated results use the signed-verifier-service pattern because the generated verifier returned false in local EVM checks even for proofs accepted by snarkjs.

## Required Production Settings

- Run with real IPFS:
  ```sh
  FAIRAI_IPFS_API=http://127.0.0.1:5001 python3 scripts/fairai_mvp.py --require-real-ipfs
  ```
- Use a persistent RPC endpoint:
  ```sh
  SEPOLIA_RPC_URL=...
  PRIVATE_KEY=...
  npx hardhat run scripts/deploy.js --network sepolia
  ```
- Pin or replicate IPFS content beyond the local Kubo node before relying on it for availability.
- Back up deployment metadata from `hardhat/deployments/<network>.json`.
- Use separate keys for admin, verifier, node operator, and aggregator roles.
- Grant `ADMIN_ROLE` to `FairAIMultisigAdmin` and then remove single-admin EOA control when moving beyond a demo.

## Remaining Production Work

- If direct on-chain Groth16 verification is required, debug or replace the generated verifier adapter before public deployment.
- Add a timelock in front of the multisig for high-value deployments.
- Add an incident response process for verifier replacement and round archival.
- Add external monitoring for contract events, IPFS pin health, and failed submissions.
- Add a real dataset adapter and privacy review before using non-synthetic data.
- Complete third-party smart-contract and ZK-verifier audits.
- Add production key management, signer rotation, and disaster-recovery procedures.
- Add persistent IPFS pinning, replication, and content availability monitoring.
- Add load tests with larger node counts and multi-round operation.
