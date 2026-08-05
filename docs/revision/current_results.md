# Current Measured Results

The FairFed and algorithmic-scaling results were generated from clean run
manifests at commit `4a08a15`. Strict infrastructure runs use clean commits
`e17a1f4` and `4fbec7a`. These are bounded local research results, not Azure,
public-chain, WAN, or production evidence.

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

## Strict Kubo and Full-Path Evidence

Two independent native Kubo 0.29.0 peers were connected over loopback. The
official Darwin ARM64 archive was verified with SHA-512
`bcd17a4913582a5715f68290bf40ef88f24c45d4cc4998fc4dbd5250d5702b155bb2189545810c6ea284f5651c2855de9ac48947d1cc0ce522a963c5a238df45`.
Thirty repetitions were measured for each payload size and concurrency level;
every retrieved byte sequence matched the published payload.

| Payload | Upload mean | Cold retrieval mean (p95) | Warm retrieval mean |
|---|---:|---:|---:|
| 1 KiB | 52.50 ms | 21.37 ms (28.65) | 0.65 ms |
| 10 KiB | 49.21 ms | 20.47 ms (26.31) | 0.54 ms |
| 100 KiB | 53.70 ms | 21.01 ms (28.35) | 0.85 ms |
| 1 MiB | 74.32 ms | 52.78 ms (72.70) | 2.71 ms |
| 10 MiB | 65.08 ms | 75.45 ms (87.48) | 23.61 ms |

For fresh 1 MiB objects, mean aggregate retrieval throughput increased from
20.55 MiB/s at concurrency 1 to 47.03 MiB/s at concurrency 20, while mean batch
latency increased from 49.34 ms to 427.21 ms.

The bounded Adult infrastructure suite executed B2, B4, and B7 for 5 and 10
clients, three seeds, and three rounds. It completed 18 isolated contract
executions, 54 archived rounds, 2,688 verified IPFS retrievals, 258 proof
decisions, 163 generated V2 proofs, 95 policy rejections without proof
generation, and 387 ledger records. No round was cancelled. This is local
single-host evidence; outage recovery and multi-host latency remain unmeasured.

## Evidence Files

- `outputs/revision_audit/fairfed-scaling-analysis/descriptive_statistics.csv`
- `outputs/revision_audit/fairfed-scaling-analysis/paired_tests.csv`
- `outputs/revision_audit/fairfed-scaling-analysis/analysis_manifest.json`
- `outputs/revision_audit/v2_proof_benchmark.json`
- `outputs/revision_audit/v2_gas_summary.csv`
- `outputs/revision_audit/v2_gas_run_manifest.json`
- `outputs/revision_audit/verifier_security_evidence.json`
- `outputs/revision_audit/verifier_security_run_manifest.json`
- `outputs/revision_audit/infrastructure-analysis/ipfs_sequential.csv`
- `outputs/revision_audit/infrastructure-analysis/ipfs_concurrency.csv`
- `outputs/revision_audit/infrastructure-analysis/bounded_metrics.csv`
- `outputs/revision_audit/infrastructure-analysis/infrastructure_summary.json`
- `outputs/revision_audit/infrastructure-analysis/analysis_manifest.json`
