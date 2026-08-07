# Ten-Seed Core Statistics

## Evidence

Two clean completed runs at commit `e01b72a` produced 120 final test rows:

- Adult: 10 seeds, 2 partitions, B0/B1/B3;
- COMPAS: 10 seeds, 2 partitions, B0/B1/B3.

Derived analysis reports means, sample standard deviations, two-sided 95%
Student-t intervals, paired t tests, Wilcoxon signed-rank checks, paired
effect-size `dz`, and Holm correction across the declared paired tests.

## Selected Results

Under strong joint non-IID:

- Adult B0 accuracy: `0.7740` (95% CI `0.7729` to `0.7751`).
- Adult B3 accuracy: `0.7629` (95% CI `0.7558` to `0.7700`).
- Adult B0 DP gap: `0.0273`; B3 DP gap: `0.0127`.
- COMPAS B0 accuracy: `0.6495` (95% CI `0.6311` to `0.6678`).
- COMPAS B3 accuracy: `0.5809` (95% CI `0.5459` to `0.6160`).
- COMPAS B0 equalized-odds gap: `0.2262`; B3: `0.1226`.

For COMPAS strong non-IID, paired B3-B0 accuracy difference was `-0.0686`
(`dz=-1.45`, Holm-adjusted paired-t `p=0.0318`). Equalized-odds difference was
`-0.1036` (`dz=-1.34`, Holm-adjusted `p=0.0491`). The policy gate therefore
shows a measured fairness/performance tradeoff, not a universal gain.

IID Adult B0 and B3 results were identical because all valid local updates met
the submitted gate. B1 is intentionally model-identical to B0 and differs only
by post-hoc assessment.

## Limits

These statistics cover B0, B1, and B3 only. They do not include real-data B2,
B4, B5, MLP, scaling, adversarial, IPFS, gas, or V2 proof overhead. The tracked
CSV and manifests are authoritative; rounded values above are explanatory.
