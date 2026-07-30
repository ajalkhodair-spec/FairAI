# Initial Real-Data Federated Results

## Classification

These are measured engineering-validation results for one predeclared seed per
dataset. They validate the real-data experiment path but are not the final
multi-seed statistical claims.

Configuration:

- 10 clients;
- 5 communication rounds;
- 3 explicit full-batch local logistic-gradient epochs;
- IID and joint label/protected-group Dirichlet alpha 0.3;
- submitted policy for B3;
- B0, B1, and B3 only.

## Adult

| Partition | Method | Test accuracy | Macro F1 | DP | EO | EOdds |
|---|---|---:|---:|---:|---:|---:|
| IID | B0/B1 | 0.7749 | 0.5250 | 0.0285 | 0.0278 | 0.0278 |
| IID | B3 | 0.7749 | 0.5250 | 0.0285 | 0.0278 | 0.0278 |
| Joint 0.3 | B0/B1 | 0.7735 | 0.5194 | 0.0267 | 0.0244 | 0.0244 |
| Joint 0.3 | B3 | 0.7592 | 0.4505 | 0.0051 | 0.0084 | 0.0084 |

## COMPAS

| Partition | Method | Test accuracy | Macro F1 | DP | EO | EOdds |
|---|---|---:|---:|---:|---:|---:|
| IID | B0/B1 | 0.6604 | 0.6425 | 0.1819 | 0.0732 | 0.2357 |
| IID | B3 | 0.6616 | 0.6419 | 0.1841 | 0.0801 | 0.2317 |
| Joint 0.3 | B0/B1 | 0.6528 | 0.6336 | 0.1683 | 0.0680 | 0.2156 |
| Joint 0.3 | B3 | 0.6098 | 0.5440 | 0.1110 | 0.0420 | 0.1480 |

## Interpretation Limits

B0 and B1 intentionally train identically; B1 adds post-hoc assessment, so
equal model outcomes are expected. B3 filters before aggregation and can trade
predictive performance for lower measured gaps.

B2, B4, and B5 were not executed in this real-data run. Their exact blockers
are recorded in each run summary. Ten independent seeds, uncertainty
intervals, paired tests, infrastructure overhead, and proof results remain
required before manuscript use.
