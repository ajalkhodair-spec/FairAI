# Clean Environment Test

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

## Unresolved G6 conditions

G6 is not fully closed because:

- a fresh Python installation could not access the package index;
- the active revision repository has no configured public remote;
- anonymous clean cloning from the final GitHub URL is unverified;
- strict Docker/Kubo execution remains denied by the task's Docker-socket
  permission boundary.

No release or public-access completion claim should be made until those
external conditions are resolved and the same protocol is rerun.
