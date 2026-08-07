# Current Measured Results

The FairFed and algorithmic-scaling results were generated from clean run
manifests at commit `4a08a15`. The bounded full-path run used clean commit
`e17a1f4`, the strict pin/cold-cache benchmark used `0d9212f`, and the isolated
publisher-recovery benchmark used `6ba3a9c`. The targeted strict adversarial run
used clean commit `3cfa695`. These are bounded local research results, not
Azure, public-chain, WAN, or production evidence.

The bounded MLP and entropy runs used clean commit `76828c3`. The current
false-metric and unavailable-artifact full-path runs used clean commit
`1536b13`.

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

## Bounded Adult MLP Matrix

The one-hidden-layer MLP was evaluated with B0, B3, and B5 under IID and joint
Dirichlet 0.3 partitions for five paired seeds, 10 clients, and five rounds.
B3 reduced mean EO gap under Dirichlet 0.3 from 0.0828 to 0.0526 while mean
accuracy decreased from 0.5514 to 0.4838. B5 produced mean accuracy 0.4806 and
EO gap 0.1160 in that partition. Under IID, B5 was close to B0 and B3 reduced
accuracy. No bounded MLP comparison remained significant after Holm correction.
These results establish model-family execution and sensitivity, not superiority
or model-family generalization.

## Metric Integrity and Storage Failure

The false-metric scenario trained a genuine model whose strict-policy decision
was rejected, replaced the reported metrics with threshold-compliant values,
generated a valid proof over those values, uploaded and retrieved the artifacts
through two Kubo peers, signed and submitted the decision, received on-chain
approval, and aggregated the CID-retrieved model. This confirms the stated trust
boundary: proof validity and artifact binding do not establish correct metric
derivation from private data.

In the unavailable-artifact scenario, three model CIDs were first approved on
chain. One approved object was then unpinned and garbage-collected from both
accessible peers. Retrieval failed, the round was cancelled on chain with reason
`APPROVED_ARTIFACT_UNAVAILABLE`, aggregation did not start, and no global model
was published.

## Entropy and Representation

The final-round B3 analysis uses 10 paired seeds. IID approval was constant at
100%, so entropy-to-approval correlation is explicitly undefined. Under
Dirichlet 0.3, group entropy correlated with approval (`rho = 0.279`,
`p = 0.005`) and inversely with excluded sample fraction (`rho = -0.265`,
`p = 0.008`). Minority-heavy clients had approval 0.62 versus 0.44 for the
other half, with mean excluded sample fractions 0.0966 and 0.1862. These are
diagnostic associations, not causal findings or an entropy-based policy rule.

## Unified Stage Timing

The current table combines only independently instrumented stages: local
training, evaluation, fairness computation, serialization, Kubo add, retrieval,
pin, witness generation, proof generation, off-chain verification, EIP-712
signing, contract submission, approved-model retrieval, aggregation, global
publication, and end-to-end runtime. Direct Solidity verification wall-clock
latency is marked unavailable; its gas result is reported separately and is not
converted into a timing value.

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

## Strict Adversarial Full-Path Evidence

B4 and B7 were each executed under no attack, label flip, sign flip, and random
weights for three paired seeds, five clients, three rounds, and a 20% malicious
cohort. The 24 clean executions used native Kubo 0.29.0, V2 Groth16 plus EIP-712
verification, and the Solidity ledger.

| Method | Attack | Mean accuracy | Mean change vs no attack | Malicious approvals |
|---|---|---:|---:|---:|
| B4 | Label flip | 0.7253 | -0.0319 | 1/9 |
| B4 | Sign flip | 0.4662 | -0.2910 | 9/9 |
| B4 | Random weights | 0.5256 | -0.2315 | 5/9 |
| B7 | Label flip | 0.5930 | -0.1837 | 1/9 |
| B7 | Sign flip | 0.4559 | -0.3208 | 9/9 |
| B7 | Random weights | 0.6396 | -0.1371 | 9/9 |

All 2,664 IPFS retrievals were byte-verified. The ledger recorded 209 approved
and 151 rejected submissions; 70 rounds were archived and two were cancelled
because no model was eligible. These results show that the fairness proof is
not a general poisoning detector. B7 reduced mean random-weight damage relative
to B4 but did not robustly prevent label- or sign-flip damage in this bounded
matrix.

## Strict Kubo and Full-Path Evidence

Two independent native Kubo 0.29.0 peers were connected over loopback. The
official Darwin ARM64 archive was verified with SHA-512
`bcd17a4913582a5715f68290bf40ef88f24c45d4cc4998fc4dbd5250d5702b155bb2189545810c6ea284f5651c2855de9ac48947d1cc0ce522a963c5a238df45`.
Thirty repetitions were measured for each payload size and concurrency level;
every retrieved byte sequence matched the published payload.

| Payload | Add mean | Cold retrieval mean (p95) | Warm retrieval mean | Pin mean |
|---|---:|---:|---:|---:|
| 1 KiB | 55.43 ms | 22.20 ms (25.36) | 0.98 ms | 19.77 ms |
| 10 KiB | 56.83 ms | 22.06 ms (26.46) | 1.52 ms | 20.72 ms |
| 100 KiB | 56.41 ms | 24.33 ms (34.80) | 1.58 ms | 20.54 ms |
| 1 MiB | 81.53 ms | 62.77 ms (74.98) | 5.74 ms | 20.65 ms |
| 10 MiB | 67.44 ms | 77.22 ms (85.93) | 20.99 ms | 17.04 ms |

For fresh 1 MiB objects, mean aggregate retrieval throughput increased from
18.44 MiB/s at concurrency 1 to 43.38 MiB/s at concurrency 10, then measured
41.73 MiB/s at concurrency 20. Mean batch latency increased from 55.04 ms to
482.51 ms.

Thirty isolated publisher-restart trials used 1 MiB payloads. Mean pin latency
was 20.45 ms; a pinned artifact remained retrievable from the consumer during
publisher outage in 5.92 ms; publisher API readiness returned in 108.78 ms; and
a newly published artifact was retrieved and verified 240.10 ms after recovery
started. Publisher identity remained stable in all repetitions.

The bounded Adult infrastructure suite executed B2, B4, and B7 for 5 and 10
clients, three seeds, and three rounds. It completed 18 isolated contract
executions, 54 archived rounds, 2,688 verified IPFS retrievals, 258 proof
decisions, 163 generated V2 proofs, 95 policy rejections without proof
generation, and 387 ledger records. No round was cancelled. This is local
single-host evidence; consumer outage, WAN, and multi-host latency remain
unmeasured.

## Evidence Files

- `outputs/revision_audit/fairfed-scaling-analysis/descriptive_statistics.csv`
- `outputs/revision_audit/fairfed-scaling-analysis/paired_tests.csv`
- `outputs/revision_audit/fairfed-scaling-analysis/analysis_manifest.json`
- `outputs/revision_audit/v2_proof_benchmark.json`
- `outputs/revision_audit/v2_gas_summary.csv`
- `outputs/revision_audit/v2_gas_run_manifest.json`
- `outputs/revision_audit/verifier_security_evidence.json`
- `outputs/revision_audit/verifier_security_run_manifest.json`
- `outputs/revision_audit/adversarial-kubo-v2-analysis/adversarial_summary.csv`
- `outputs/revision_audit/adversarial-kubo-v2-analysis/adversarial_approval.csv`
- `outputs/revision_audit/adversarial-kubo-v2-analysis/adversarial_infrastructure.json`
- `outputs/revision_audit/adversarial-kubo-v2-analysis/ledger_receipts.csv`
- `outputs/revision_audit/adversarial-kubo-v2-analysis/proof_decisions.csv`
- `outputs/revision_audit/adversarial-kubo-v2-analysis/ipfs_retrieval_checks.csv`
- `outputs/revision_audit/adversarial-kubo-v2-analysis/analysis_manifest.json`
- `outputs/revision_audit/infrastructure-analysis-v2/ipfs_sequential.csv`
- `outputs/revision_audit/infrastructure-analysis-v2/ipfs_concurrency.csv`
- `outputs/revision_audit/infrastructure-analysis-v2/ipfs_recovery.csv`
- `outputs/revision_audit/infrastructure-analysis-v2/bounded_metrics.csv`
- `outputs/revision_audit/infrastructure-analysis-v2/infrastructure_summary.json`
- `outputs/revision_audit/infrastructure-analysis-v2/analysis_manifest.json`
- `outputs/revision_audit/expanded-analysis-6df6bfb/analysis_manifest.json`
- `outputs/revision_audit/entropy-approval-4d97043/analysis_manifest.json`
- `outputs/revision_audit/stage-timing-1536b13/analysis_manifest.json`
- `outputs/revision_audit/stage-timing-1536b13/stage_timing.csv`
- `outputs/revision_audit/trust-boundary-1536b13/evidence.json`
