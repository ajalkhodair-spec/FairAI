# Major Revision Execution Runbook

Run commands from the repository root.

## Phase 0

```sh
git status --short --branch
git branch --show-current
git remote -v
git log --oneline --decorate -n 20
gh auth status
python3 -m unittest discover -s tests
(cd hardhat && npm ci && npm test)
```

Record failures without deleting partial evidence.

## Service Checks

```sh
docker --version
docker compose version
docker compose -f docker-compose.ipfs.yml up -d
curl -fsS -X POST http://127.0.0.1:5001/api/v0/version
```

Strict IPFS runs must fail if Kubo is unavailable.

## Existing Legacy Commands

```sh
python3 scripts/fairai_mvp.py \
  --output outputs/major_revision/legacy_mvp/single \
  --require-real-ipfs

FAIRAI_IPFS_API=http://127.0.0.1:5001 \
python3 scripts/run_experiments.py \
  --output outputs/major_revision/legacy_mvp \
  --trials 3 \
  --require-real-ipfs
```

The legacy ZK path additionally requires a compatible `circom`, `snarkjs`, and
`FAIRAI_PTAU_PATH` or `zk/powersoftau_final.ptau`.

## Recovery

- Do not delete failed run directories.
- Mark completion status and error in the run manifest.
- Resume only stages whose output checksums and schemas validate.
- Never use local content-addressed fallback for strict IPFS evidence.
- Never overwrite `results/q1_results_package/`.

## Unified Interface

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m fairai_revision.datasets adult
.venv/bin/python -m fairai_revision.datasets compas
make test PYTHON=.venv/bin/python
.venv/bin/python -m fairai_revision.run --config configs/revision/legacy_mvp.yaml
make test
make revision-smoke
```

Dataset downloads are checksum-enforced. A mismatch aborts preparation rather
than substituting another source. Scenario configurations with
`executor: planned` remain fail-closed until their phase is implemented.

## Gas and Local Throughput

```sh
.venv/bin/python -m fairai_revision.run \
  --config configs/revision/gas_benchmark.yaml \
  --run-id gas-throughput-30rep
```

The executor runs the per-operation gas benchmark and the sequential/concurrent
submission benchmark. Results are local Hardhat evidence, not public-chain
throughput.

## Statistics and Publication Package

```sh
.venv/bin/python -m fairai_revision.statistics \
  --input outputs/major_revision/adult-core-10seed-e01b72a \
  --input outputs/major_revision/compas-core-10seed-e01b72a \
  --output outputs/major_revision/core-statistics-bootstrap

.venv/bin/python -m scripts.analyze_expanded_results \
  --mlp outputs/major_revision/adult-mlp-5seed-ee23a65 \
  --scaling outputs/major_revision/client-scaling-5seed-2d2b220 \
  --heterogeneity outputs/major_revision/heterogeneity-10seed-2d2b220 \
  --threshold outputs/major_revision/threshold-sensitivity-10seed-aa165b3 \
  --adversarial outputs/major_revision/adversarial-5seed-e8733cb \
  --output outputs/major_revision/expanded-analysis-bootstrap

.venv/bin/python -m scripts.prepare_results_package \
  --gas-run gas-throughput-30rep \
  --analysis-run expanded-analysis-bootstrap \
  --core-analysis-run core-statistics-bootstrap
.venv/bin/python -m scripts.build_latex_tables
.venv/bin/python -m scripts.build_revision_figures
.venv/bin/python scripts/render_revision_png_figures.py
node scripts/build_results_workbook.mjs
```

PNG rendering additionally requires `requirements-report.txt`. The workbook
step requires `@oai/artifact-tool`.

## Strict IPFS Benchmark

```sh
docker compose -f docker-compose.ipfs.yml down -v
docker compose -f docker-compose.ipfs.yml up -d --wait
.venv/bin/python -m fairai_revision.run \
  --config configs/revision/ipfs_benchmark.yaml \
  --run-id ipfs-two-peer-30rep
```

Do not publish IPFS result tables unless the manifest is completed and records
both real peer IDs and the pinned Kubo version.

## Focused Trust-Boundary Runs

Use fresh Kubo volumes between the two scenarios because the unavailable-CID
test intentionally unpins and garbage-collects an approved object.

```sh
docker compose -f docker-compose.ipfs.yml down -v
docker compose -f docker-compose.ipfs.yml up -d --wait
.venv/bin/python -m fairai_revision.run \
  --config configs/revision/false_metric_reporting.yaml

docker compose -f docker-compose.ipfs.yml down -v
docker compose -f docker-compose.ipfs.yml up -d --wait
.venv/bin/python -m fairai_revision.run \
  --config configs/revision/approved_artifact_failure.yaml
```

The first run is expected to archive a round containing the fabricated-metric
model. The second is expected to complete as a negative test with an on-chain
`Cancelled` state, reason `APPROVED_ARTIFACT_UNAVAILABLE`, and no global model.
