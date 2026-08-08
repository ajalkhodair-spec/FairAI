# FairAI Research Implementation

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21838694.svg)](https://doi.org/10.5281/zenodo.21838694)

FairAI is a manifest-driven research implementation of fairness-gated
federated learning with smart-contract governance and IPFS artifact
traceability. It preserves the submitted three-node MVP and adds real-data,
multi-seed, multi-round, and bounded multi-host validation infrastructure.

This repository is not a security-audited production deployment. It is a
reproducible, bounded local research implementation with explicit scientific
nonclaims.

## Demonstrated Scope

- checksum-pinned Adult and COMPAS acquisition;
- train-only tabular preprocessing;
- federated logistic regression and a deterministic small MLP;
- IID and label/group Dirichlet client partitions;
- 3, 5, 10, 20, and 50 logical-client experiments;
- demographic parity, equal opportunity, equalized odds, and subgroup
  accuracy gaps;
- versioned fairness-policy profiles and approved-only aggregation;
- per-round on-chain eligibility checks followed by CID retrieval and
  aggregation of the retrieved model parameters;
- sample-weighted FedAvg and coordinate-wise median;
- the published FairFed server weighting rule with signed EOD and accuracy
  fallback;
- Solidity roles, node registration, duplicate-CID rejection, round lifecycle,
  eligible-model retrieval, global-model publication, and audit events;
- EIP-712 verifier decisions with domain separation, expiry, revocation, and
  nonce/digest replay protection;
- packaged V2 R1CS/WASM/ZKey/VKey artifacts whose manifest declares Circom
  2.1.6, direct Groth16 verification, composite proof/signature approval, and
  cryptographic negative tests;
- strict B2/B4/B7 two-peer Kubo adapters and three-host Azure deployment
  infrastructure;
- deterministic poisoning scenarios and A1-A14 security evidence;
- full-path false-metric and approved-artifact-unavailable trust-boundary tests;
- repeated Hardhat gas and sequential/concurrent throughput measurements, plus
  modeled cost scenarios;
- run manifests, statistical tables, a 40-sheet workbook, and figure-data
  exports.

## Boundaries

- The V2 phase-2 setup has one experimental contributor. A governed multi-party
  ceremony is required before production deployment.
- Strict local two-peer Kubo timings, publisher outage/recovery, and B2/B4/B7
  runs are included. Consumer outage, WAN behavior, Docker Compose, and Azure
  execution are not claimed as measured evidence.
- FairFed implements the published server aggregation rule; it does not claim
  to reproduce every local debiasing variant from the paper.
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
- Docker Desktop for Compose-based Kubo scenarios, or two native Kubo 0.29.0
  peers for `ipfs_benchmark_native.yaml`
- Circom 2.1.6 and snarkjs 0.7.5 for V2 artifact regeneration

The tracked V2 artifact manifest declares Circom 2.1.6, but the archive does
not contain a contemporaneous compiler transcript proving that declaration;
see [circom_version_reconciliation.md](docs/revision/circom_version_reconciliation.md).

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

Run the two focused trust-boundary scenarios from fresh Kubo volumes:

```sh
docker compose -f docker-compose.ipfs.yml down -v
docker compose -f docker-compose.ipfs.yml up -d --wait
python -m fairai_revision.run --config configs/revision/false_metric_reporting.yaml

docker compose -f docker-compose.ipfs.yml down -v
docker compose -f docker-compose.ipfs.yml up -d --wait
python -m fairai_revision.run --config configs/revision/approved_artifact_failure.yaml
```

The tracked native-peer configuration and bounded full-path suite are:

```sh
make revision-ipfs-native
make revision-kubo-v2
make revision-kubo-v2-adversarial
```

The committed derived evidence is under
`outputs/revision_audit/infrastructure-analysis-v2/`.
The strict poisoning analysis is under
`outputs/revision_audit/adversarial-kubo-v2-analysis/`.
The native Kubo archive used for those measurements is pinned in
`infrastructure/toolchain.lock.json`.

Run the isolated publisher outage/recovery benchmark with the pinned binary:

```sh
FAIRAI_KUBO_BINARY=/absolute/path/to/ipfs make revision-ipfs-recovery
```

Run the measured V2 proof benchmark without Docker:

```sh
make revision-proof
```

The tracked V2 bundle is checksum-validated before every proof. The benchmark
labels its single-contributor setup and does not imply a production ceremony.

## Azure Matrix

The bounded Azure topology uses three physical hosts and distributes 5, 10, or
20 logical clients across two workers. The local scaling experiment reaches 50
logical clients; neither count should be described as a VM count.

Deployment, private Kubo setup, remote-worker configuration, matrix execution,
result upload, and teardown are documented in [azure/README.md](azure/README.md).
The Bicep template compiles locally, but no Azure resources or Azure results are
claimed in the repository until a subscription owner runs and records them.

## Report Generation

```sh
python -m scripts.prepare_results_package --primary-csv-only
python -m scripts.build_latex_tables
python -m scripts.build_revision_figures
python scripts/render_revision_png_figures.py
node scripts/build_results_workbook.mjs
python -m scripts.build_blocker_view
python -m scripts.build_reviewer_evidence_views
python -m scripts.build_release_checksums
python -m scripts.build_closure_evidence
```

The `--primary-csv-only` mode rebuilds the workbook payload from the 40 tracked
canonical CSV sheets. Omit the flag only when the complete raw run directories
listed by the experiment package are present. The workbook builder uses
`@oai/artifact-tool`; install it in the report environment before running that
command.
The committed publication package also includes deterministic bootstrap
statistics and SHA-256 release checksums.

Primary tracked evidence is under `outputs/major_revision/`. Each measured run
contains a manifest with its commit, configuration hash, dataset checksum,
partition checksum, timestamps, and completion status. The output directory
contract is documented in
[output_schema.md](docs/revision/output_schema.md).

The canonical editable paper source is `manuscript/FairAI.tex`. Build it from
the `manuscript/` directory with:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error FairAI.tex
```

Before a release, require the generated views and both integrity layers to be
current:

```sh
python -m scripts.build_blocker_view --verify
python -m scripts.build_reviewer_evidence_views --verify
python -m scripts.build_release_checksums --verify
python -m scripts.build_closure_evidence --verify
```

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

Use [CITATION.cff](CITATION.cff). Release `v0.2.1` is archived under version DOI
`10.5281/zenodo.21838695`; concept DOI `10.5281/zenodo.21838694` resolves to the
latest archived version. Closure changes made after `v0.2.1` require a new
immutable GitHub release and Zenodo version before they are cited as published.

## License

MIT. See [LICENSE](LICENSE).
