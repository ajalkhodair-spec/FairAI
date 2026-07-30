# Formal Legacy Reproduction

The configuration-driven runner executed `legacy_mvp_reproduction` three times
with strict Kubo/IPFS and the Version 1 signed-verifier pathway.

## Comparison Result

All twelve configured baseline checks matched:

- six node accuracy/DP values;
- approved and rejected counts;
- global accuracy;
- global DP gap;
- approval rate;
- global publication gas.

Numeric metrics used absolute tolerance `1e-4`. Gas used exact comparison.
Fresh timing values remain measured observations and are not forced to match the
submitted run.

## Evidence Files

- `outputs/major_revision/legacy_mvp/reproduction_summary.json`
- `outputs/major_revision/legacy_mvp/baseline_comparison.json`
- `outputs/major_revision/legacy_mvp/node_metrics.csv`
- `outputs/major_revision/legacy_mvp/global_metrics.csv`
- `outputs/major_revision/legacy_mvp/gas.csv`
- `outputs/major_revision/legacy_mvp/artifact_inventory.csv`
- `outputs/major_revision/legacy_mvp/proof_timings.csv`
- `outputs/major_revision/legacy_mvp/ipfs_timings.csv`
- `outputs/major_revision/legacy_mvp/lifecycle.json`

Each formal trial has its own run manifest under
`raw/trial_<n>/manifests/run_manifest.json`.

Dataset and partition checksums remain explicitly missing because the Version 1
runner did not serialize its generated records. Phase 3 infrastructure will
make dataset and partition provenance first-class evidence; the legacy code is
not retroactively changed.

