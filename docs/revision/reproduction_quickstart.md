# Reproduction Quickstart

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-lock.txt
cd hardhat && npm ci && cd ..
make test
make revision-smoke
make revision-proof
```

For one real-data federated scenario after checksum-pinned Adult acquisition:

```sh
python -m fairai_revision.run \
  --config configs/revision/scaling.yaml \
  --run-id scaling-reproduction
```

For strict Kubo:

```sh
docker compose -f docker-compose.ipfs.yml up -d --wait
make revision-ipfs
```

The strict Kubo benchmark fails rather than substituting local fallback CIDs.
GitHub Actions runs the shorter `configs/revision/ci_ipfs.yaml` protocol using
real Kubo peers. The 30-repetition tracked benchmark, not the CI smoke, is the
source of publication timing results.

The legacy full-path reproduction additionally requires Circom 2.1.6,
snarkjs 0.7.5, and an externally acquired phase-2 Powers of Tau file at
`zk/powersoftau_final.ptau`. It is not part of the dependency-only quickstart.

For report data and figures:

```sh
python scripts/prepare_results_package.py --primary-csv-only
python scripts/build_revision_figures.py
python scripts/render_revision_png_figures.py
```

The workbook additionally requires `@oai/artifact-tool` in the Node report
environment. Every completed scenario must end with a clean run manifest. Do
not treat a failed or dirty-tree manifest as publication evidence.
