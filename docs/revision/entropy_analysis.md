# Client Partitioning and Entropy Analysis

## Scope

Phase 4 implements deterministic IID, label-Dirichlet, and joint
label/protected-group Dirichlet partitions. The required concentration values
are `1.0` and `0.3`; `0.3` is the primary strong non-IID setting.

Protected attributes are used only to define joint strata and diagnostics. They
remain excluded from model features and entropy is not an approval criterion.

## Reproduction

Acquire the checksum-pinned Adult data, then run:

```sh
.venv/bin/python -m fairai_revision.datasets adult
make revision-partitions PYTHON=.venv/bin/python
```

The unified runner writes its manifest to
`outputs/major_revision/heterogeneity-partitions/manifests/run_manifest.json`.
Partition evidence is under the run's `partitions/` directory.

## Algorithms

IID partitioning applies one seeded permutation and balanced array splitting.
Dirichlet partitioning processes each label or joint label/group stratum,
samples client proportions from `Dirichlet(alpha)`, and allocates every row
exactly once. A partition is accepted only when every client reaches the
configured minimum size. The deterministic retry loop is bounded and fails
explicitly if no valid partition is found.

Each partition checksum is SHA-256 over canonical JSON containing the mode,
seed, alpha, minimum size, and sorted row indices for every client.

For a client distribution \(p\) over \(K\) observed-domain categories,
normalized entropy is:

```text
H = -sum(p_k * log(p_k)) / log(K)
```

Source entropy applies the same normalization to each client's fraction of the
training data. Values range from 0 for concentration in one category/source to
1 for a uniform distribution.

## Measured Validation

The Phase 4 validation used the 25,637-row Adult training split, 10 clients,
seed 6001, and a minimum of 50 samples per client.

| Partition | Mean label entropy | Mean group entropy | Source entropy |
|---|---:|---:|---:|
| IID | 0.8091 | 0.9088 | 1.0000 |
| Label Dirichlet 1.0 | 0.5699 | 0.8568 | 0.9229 |
| Label Dirichlet 0.3 | 0.4677 | 0.8727 | 0.8515 |
| Joint Dirichlet 1.0 | 0.7371 | 0.7778 | 0.9267 |
| Joint Dirichlet 0.3 | 0.4668 | 0.4049 | 0.7814 |

All five settings covered every training row exactly once and met the minimum
client size. These values are measured diagnostics from the current local run;
the ignored output package, not this rounded table, is the authoritative
machine-readable evidence.

## Deferred Correlations

Accuracy, DP gap, EO gap, approval, and exclusion are produced by later model,
fairness-policy, and federated-training phases. Phase 4 writes their correlation
rows with `status=undefined` and a reason instead of inventing zeros. The rows
will be replaced by measured coefficients after those outcomes exist.
