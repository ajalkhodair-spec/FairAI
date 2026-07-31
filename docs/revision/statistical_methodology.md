# Statistical Methodology

## Experimental unit and pairing

The independent experimental unit is the configured seed. Methods compared
within a suite use the same seed, client partition, train/validation/test split,
initial model, round count, local epochs, optimizer, and batch semantics. The
analysis rejects duplicate `(scenario, seed, partition, method)` keys.

Three-run legacy results are descriptive regression evidence only. Inferential
comparisons use the ten-seed core suites or the five-seed bounded validation
suites, and their sample counts are always reported.

## Descriptive statistics

For every available metric and configuration group, the publication tables
report:

- sample count;
- mean;
- sample standard deviation;
- median;
- minimum;
- maximum;
- a two-sided 95% percentile bootstrap interval for the mean.

Bootstrap intervals use 10,000 resamples. A stable SHA-256-derived seed binds
the random generator to the suite, dimensions, and metric, making regeneration
deterministic. Constant and single-observation samples return a degenerate
interval and are not presented as inferential evidence.

## Paired comparisons

Available paired method comparisons report a paired t-test and a Wilcoxon
signed-rank check. Holm correction is applied across the reported paired
t-tests. Effect sizes are paired Cohen's `dz` and matched-pairs rank-biserial
correlation. Zero-difference and constant-difference cases are handled
explicitly rather than passed to numerically unstable test calls.

The tests describe the measured seed set. They do not establish external
validity beyond the datasets, models, policies, partitions, attacks, and local
infrastructure that were executed.

## Microbenchmarks

Thirty-repetition infrastructure summaries report mean, sample standard
deviation, median, interquartile range, p95, minimum, maximum, and failures
where the underlying measurement exists. Hardhat throughput is local,
in-process evidence and must not be interpreted as public-chain throughput.
Kubo statistics remain missing until the strict two-peer Docker benchmark can
access the Docker daemon.

## Machine-readable outputs

The publication exports are:

- `outputs/major_revision/descriptive_statistics.csv`
- `outputs/major_revision/confidence_intervals.csv`
- `outputs/major_revision/paired_tests.csv`
- `outputs/major_revision/corrected_p_values.csv`
- `outputs/major_revision/effect_sizes.csv`

Each derived package records source paths and hashes in its analysis manifest.
