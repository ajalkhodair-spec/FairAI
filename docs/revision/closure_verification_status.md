# Closure Verification Status

## Completed checks

- On 2026-08-10, an anonymous depth-one clone of public tag `v0.3.0` installed
  the exact Python lock under Python 3.11 and the Node lock under Node 20. All
  82 Python and 22 Solidity tests passed. The smoke scenario and a real
  two-peer Kubo 0.29.0 Docker Compose functional benchmark also completed.

- Manuscript source hash matches the imported original:
  `edd73c6efae0d714c5419e590f4b773825bf59f6a01d6a14bb88a7ae54ca4555`.
- A clean temporary-directory `latexmk` build completed successfully and
  produced a 23-page PDF on 2026-08-08. The build completed without fatal
  errors; LaTeX reported non-fatal layout and header-height warnings.
- The 331-entry major-revision release checksum manifest verifies with zero
  missing files and zero mismatches.
- The closure checksum manifest and evidence freeze verify against all selected
  canonical targets.
- The standalone packaged V2 proof integration test passed using the committed
  artifacts and local snarkjs `0.7.5` executable. It did not recompile the
  circuit.
- The dependency-free closure and packaged-proof subset passed 6/6 tests on
  2026-08-08. All blocker, reviewer-evidence, release-checksum, and closure
  generators passed their `--verify` modes, and `git diff --check` passed.
- The consolidated workbook was rebuilt from all 40 canonical primary CSV
  sheets, inspected for the corrected blocker and reviewer rows, scanned with
  zero formula-error matches, and visually reviewed sheet by sheet.
- The complete Python suite passed 82/82 tests in an existing project-lineage
  Python 3.13.5 environment. Pandas 3.0.3 and scikit-learn 1.9.0 matched the
  lock; NumPy 2.5.1 and SciPy 1.18.0 were newer than the locked 2.4.6 and
  1.17.1 versions. This is compatibility evidence, not an exact-pinned run.
- The complete Solidity suite passed 22/22 tests using Hardhat 2.28.6,
  `@nomicfoundation/hardhat-toolbox` 6.1.2, and snarkjs 0.7.5. Those versions
  match the committed Node lockfile.

## Historical environment-blocked checks

The complete validation suite could not run in the earlier isolated workspace:

- A clean `.venv` was created and `pip install -r requirements-lock.txt` was
  attempted on 2026-08-08. The install could not reach PyPI because DNS/network
  access is unavailable; Python scientific dependencies (`numpy`, `pandas`,
  and `pytest`) therefore remain absent.
- `npm ci` was attempted against the committed lockfile on 2026-08-08. The npm
  registry could not be resolved, so Hardhat project dependencies remain
  unavailable and the Solidity suite could not be rerun in this workspace.
- Docker daemon access is denied to this workspace, so containerized fallback
  validation was not available.

The system-Python discovery executed 37 entries: 27 passed and 10 ended in
import errors caused by missing scientific dependencies. The bundled document
runtime improved this to 61 passing entries and six environment errors. The
separate project-lineage environment then passed all 82 tests as recorded
above. The later public-release verification closed the exact-pinned and Docker
functional gaps; these details are retained to distinguish historical sandbox
limitations from repository failures.

## Release gate

Status: `CLOSED_WITH_DOCUMENTED_LIMITATIONS`

Release `v0.3.0` is publicly accessible and archived. Its exact-pinned clean
installation, complete test suites, smoke scenario, and functional Kubo path
have been independently rerun. BLK-005, the single-contributor experimental
ZKey, and unmeasured WAN, multi-host, public-chain, and consumer-outage cases
remain explicit limitations rather than release-gate failures.
