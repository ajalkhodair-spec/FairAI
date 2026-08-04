# Current Measured Results

These results were generated from clean run manifests at commit `4a08a15`.
They are bounded local research evidence, not Azure, public-chain, production, or
strict two-peer Kubo measurements.

## FairFed Comparison

Each row is the mean over 10 paired seeds after five communication rounds with
10 clients. The interval is a deterministic percentile-bootstrap 95% CI. Lower
equal-opportunity (EO) gap is favorable; higher accuracy is favorable.

| Dataset | Partition | Method | Accuracy (95% CI) | EO gap (95% CI) |
|---|---|---|---|---|
| Adult | IID | B0 | 0.7746 [0.7745, 0.7748] | 0.0261 [0.0251, 0.0271] |
| Adult | IID | B5 FairFed | 0.7749 [0.7746, 0.7751] | 0.0261 [0.0251, 0.0271] |
| Adult | Dirichlet 0.3 | B0 | 0.7752 [0.7733, 0.7777] | 0.0306 [0.0266, 0.0367] |
| Adult | Dirichlet 0.3 | B5 FairFed | 0.6474 [0.5315, 0.7505] | 0.0112 [0.0007, 0.0299] |
| COMPAS | IID | B0 | 0.6562 [0.6549, 0.6576] | 0.1270 [0.1235, 0.1311] |
| COMPAS | IID | B5 FairFed | 0.6549 [0.6509, 0.6585] | 0.1283 [0.1217, 0.1360] |
| COMPAS | Dirichlet 0.3 | B0 | 0.6462 [0.6327, 0.6559] | 0.1416 [0.1186, 0.1721] |
| COMPAS | Dirichlet 0.3 | B5 FairFed | 0.5423 [0.5144, 0.5721] | 0.0428 [0.0092, 0.0923] |

FairFed was effectively neutral under IID partitions. Under stronger
heterogeneity it reduced mean EO gap but also reduced accuracy by 0.1278 on
Adult and 0.1039 on COMPAS. The COMPAS accuracy reduction remained significant
after Holm correction (`p = 0.0032`); the corresponding EO-gap result did not
(`p = 0.2109`). This is evidence of an accuracy-fairness trade-off, not evidence
that B5 dominates FedAvg.

## Algorithmic Scaling

B5 was executed for five seeds at 3, 5, 10, 20, and 50 logical clients. Mean
runtime increased from 51.3 ms at three clients to 220.1 ms at 50 clients for
the local sequential implementation. At 50 clients, mean accuracy was 0.7542
and mean EO gap was 0.0000. The zero gap must be interpreted with the accuracy,
F1, prediction-rate, and subgroup evidence because a degenerate classifier can
produce an apparently favorable group gap.

## Cryptographic and Contract Evidence

- V2 Groth16: 30 valid proofs verified and six negative cases rejected.
- Mean witness, proof, and off-chain verification times were 30.68 ms, 257.51
  ms, and 213.59 ms respectively.
- Direct V2 verifier deployment used 1,001,364 gas.
- Each of 30 direct V2 verification transactions used 348,811 gas on Hardhat
  chain ID 31337.
- The security executor recorded 18 passing contract cases covering proof
  binding, authorization, tampering, replay, expiry, revocation, lifecycle, and
  global publication.

The ZKey is a single-contributor experimental setup. No production ceremony,
external cryptographic audit, public-chain cost, or production security claim is
made.

## Evidence Files

- `outputs/revision_audit/fairfed-scaling-analysis/descriptive_statistics.csv`
- `outputs/revision_audit/fairfed-scaling-analysis/paired_tests.csv`
- `outputs/revision_audit/fairfed-scaling-analysis/analysis_manifest.json`
- `outputs/revision_audit/v2_proof_benchmark.json`
- `outputs/revision_audit/v2_gas_summary.csv`
- `outputs/revision_audit/v2_gas_run_manifest.json`
- `outputs/revision_audit/verifier_security_evidence.json`
- `outputs/revision_audit/verifier_security_run_manifest.json`
