# Clean Environment Test

## Current public-release verification

On 2026-08-10, an anonymous depth-one clone of public tag `v0.3.0` resolved to
commit `6c064d0d3e01d0b6493b6650cb781379c7044fcd`. A newly created Python 3.11
environment installed every exact version in `requirements-lock.txt`, and
`npm ci` installed the committed Hardhat lockfile. From the repository root:

- all 82 Python tests passed;
- all 22 Solidity tests passed;
- the revision smoke scenario completed;
- a short real two-peer Kubo 0.29.0 Docker Compose benchmark completed with
  three repetitions, four payload sizes, and concurrency 1/5/10.

This closes the former public-remote, exact-pinned-install, anonymous-clone,
and Docker functional-integration gaps. The 30-repetition native Kubo archive
remains the source of publication performance results; the short Compose run
is a functional reviewer check.

The documented legacy full-path command is not self-contained because
`zk/powersoftau_final.ptau` is intentionally not versioned. It requires Circom
2.1.6, snarkjs 0.7.5, and an externally acquired phase-2 Powers of Tau file.
Core tests, packaged V2 proof verification, smoke execution, and the strict
IPFS benchmark do not require that file.

## Scope and commits

- Clean-clone source/test commit: `846a068`
- Clean report-package commit: `f62a3ad`
- Branch: `major-revision-experiments`
- Clone mode: `git clone --no-local`
- Platform: macOS arm64, Python 3.13.5, Node.js 24.4.1

The commits between `846a068` and `f62a3ad` add only the legacy report manifest
and required legacy summary evidence. No implementation or test code changes
occur between those commits.

## Installation

The no-local clone completed successfully and was clean.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --retries 0 --timeout 5 \
  -r requirements-lock.txt
```

Result: blocked after 0.28 seconds because the execution sandbox could not
resolve the package index. Pip reported no available `joblib==1.5.2` candidate;
the same pinned requirements are installed and tested in the source
environment. This is recorded as a network-isolation failure, not as a passing
clean Python installation.

```sh
cd hardhat
npm ci --prefer-offline --no-audit
```

Result: passed independently. npm installed 582 packages in 10.25 seconds.

## Tests and smoke scenario

With the verified pinned Python environment supplied explicitly through
`PYTHON=...`, the clean clone produced:

- 59 Python tests passed;
- 15 Solidity tests passed;
- `revision-smoke` completed;
- total `make test` elapsed time: 13.27 seconds;
- smoke elapsed time: 0.78 seconds.

The Python dependency directory was not copied into the repository and the Git
working tree remained clean.

## Adult real-data scenario

The checksum-pinned Adult download command failed because DNS was unavailable.
After that failure was preserved, the previously downloaded raw files were
copied into the ignored `data/raw/` location. Their hashes matched:

- `adult.data`:
  `5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d`
- `adult.test`:
  `a2a9044bc167a35b2361efbabec64e89d69ce82d9790d2980119aac5fd7e9c05`

The following external-output-root run completed in 11.77 seconds:

```sh
python -m fairai_revision.run \
  --config configs/revision/adult_core.yaml \
  --output-root /tmp/fairai-clean-adult-final \
  --run-id adult-clean-846a068
```

The run used 10 seeds, five rounds, 10 clients, IID and joint Dirichlet
partitions, and B0/B1/B3 as specified by the tracked configuration. Its
manifest reports `completion_status=completed`.

The test exposed and led to correction of an output-path formatting defect:
external output roots now print an absolute path rather than failing after a
successful run.

## Report regeneration

At `f62a3ad`, these commands completed from another no-local clone:

```sh
python -m scripts.prepare_results_package
python -m scripts.build_latex_tables
python -m scripts.build_revision_figures
```

The following regenerated files matched the committed SHA-256 hashes exactly:

- `outputs/major_revision/descriptive_statistics.csv`
- `outputs/major_revision/latex_tables/baseline_comparison.tex`
- `outputs/major_revision/figures_independent/baseline_comparison.svg`

The working tree remained clean after regeneration.

## Historical G6 conditions

The earlier sandbox run could not close G6 because:

- a fresh Python installation could not access the package index;
- the active revision repository has no configured public remote;
- anonymous clean cloning from the final GitHub URL is unverified;
- strict Docker/Kubo execution remains denied by the task's Docker-socket
  permission boundary.

Those conditions were subsequently resolved by the public `v0.3.0` clean-clone
verification recorded above.
