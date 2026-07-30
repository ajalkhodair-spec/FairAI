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

## Planned Unified Interface

```sh
python -m fairai_revision.run --config configs/revision/legacy_mvp.yaml
make test
make revision-smoke
```

These commands are planned and are not yet implemented.

