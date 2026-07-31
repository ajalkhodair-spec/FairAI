# FairAI Research Implementation

FairAI is a manifest-driven research implementation of fairness-gated
federated learning with smart-contract governance and IPFS artifact
traceability. It preserves the submitted three-node MVP and adds real-data,
multi-seed, multi-round validation infrastructure.

This repository is not a security-audited production deployment. It is a
tested research prototype with production-oriented controls and explicit
scientific nonclaims.

## Demonstrated Scope

- checksum-pinned Adult and COMPAS acquisition;
- train-only tabular preprocessing;
- federated logistic regression and a deterministic small MLP;
- IID and label/group Dirichlet client partitions;
- 3, 5, 10, and 20-client experiments;
- demographic parity, equal opportunity, equalized odds, and subgroup
  accuracy gaps;
- versioned fairness-policy profiles and approved-only aggregation;
- sample-weighted FedAvg and coordinate-wise median;
- Solidity roles, node registration, duplicate-CID rejection, round lifecycle,
  eligible-model retrieval, global-model publication, and audit events;
- EIP-712 verifier decisions with domain separation, expiry, revocation, and
  nonce/digest replay protection;
- deterministic poisoning scenarios and A1-A14 security evidence;
- repeated Hardhat gas and sequential/concurrent throughput measurements, plus
  modeled cost scenarios;
- run manifests, statistical tables, a 37-sheet workbook, and figure-data
  exports.

## Boundaries

- V2 proof binding source and negative tests exist, but direct V2 Groth16
  artifacts are blocked until Circom 2.1.6 and the pinned Powers of Tau file are
  available.
- The two-peer Kubo benchmark is strict and implemented, but current repository
  evidence does not include its timings because Docker socket access was
  unavailable during the recorded run.
- FairFed is not labeled as implemented; no custom heuristic substitutes for a
  faithful primary-paper implementation.
- Raw training data stay local, but the implementation does not provide a
  formal guarantee against membership inference, model inversion,
  model-update leakage, or metadata leakage.
- Fairness is the directly operationalized ethical dimension. The system does
  not mathematically evaluate all ethical principles.

See [BLOCKERS.md](BLOCKERS.md), [privacy_scope.md](docs/revision/privacy_scope.md),
and [known_undetected_threats.md](docs/revision/known_undetected_threats.md).

## Requirements

- Python 3.11 or newer
- Node.js 20
- Docker Desktop for strict Kubo scenarios
- Circom 2.1.6 and snarkjs 0.7.5 for V2 artifact regeneration

Install:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-lock.txt
cd hardhat
npm ci
cd ..
```

Install report-only dependencies when regenerating PNG figures:

```sh
python -m pip install -r requirements-report.txt
```

## Verification

```sh
make test
make revision-smoke
```

Run the submitted-state reproduction with strict Kubo:

```sh
docker compose -f docker-compose.ipfs.yml up -d --wait
FAIRAI_IPFS_API=http://127.0.0.1:5001 \
  python -m fairai_revision.run \
  --config configs/revision/legacy_mvp.yaml \
  --run-id legacy_mvp
```

Run core and expanded experiments:

```sh
make revision-core
python -m fairai_revision.run --config configs/revision/adult_mlp.yaml
make revision-scaling
python -m fairai_revision.run --config configs/revision/heterogeneity.yaml
make revision-fairness
python -m fairai_revision.run --config configs/revision/adversarial.yaml
python -m fairai_revision.run --config configs/revision/gas_benchmark.yaml
```

Run the strict two-peer IPFS benchmark:

```sh
docker compose -f docker-compose.ipfs.yml up -d --wait
make revision-ipfs
```

The benchmark fails if either real Kubo endpoint is unavailable. It never
records fallback CIDs as IPFS evidence.

## Report Generation

```sh
python -m scripts.prepare_results_package
python -m scripts.build_latex_tables
python -m scripts.build_revision_figures
python scripts/render_revision_png_figures.py
node scripts/build_results_workbook.mjs
```

The workbook builder uses `@oai/artifact-tool`; install it in the report
environment before running that command.
The committed publication package also includes deterministic bootstrap
statistics and SHA-256 release checksums.

Primary tracked evidence is under `outputs/major_revision/`. Each measured run
contains a manifest with its commit, configuration hash, dataset checksum,
partition checksum, timestamps, and completion status. The output directory
contract is documented in
[output_schema.md](docs/revision/output_schema.md).

## Data Preparation

Dataset source URLs, license notes, and checksums are recorded in
`data/raw/<dataset>/download_manifest.json` when acquisition is run. Raw data
are ignored by Git. Dataset loaders reject checksum mismatches and fit
preprocessing only on the training split.

## Troubleshooting

- Docker permission errors: grant the shell access to Docker Desktop's socket,
  then rerun the strict Kubo command.
- Circom mismatch: run `python scripts/check_zk_toolchain.py`; do not use
  legacy circuit artifacts as V2 evidence.
- Existing output directory: choose a new `--run-id`, or use `--resume` only
  with the identical configuration.
- Missing raw datasets: run the checksum-pinned acquisition command documented
  in [EXECUTION_RUNBOOK.md](docs/revision/EXECUTION_RUNBOOK.md).

## Citation

Use [CITATION.cff](CITATION.cff). Public repository accessibility must be
verified anonymously before citing the repository URL as an available artifact.

## License

MIT. See [LICENSE](LICENSE).
