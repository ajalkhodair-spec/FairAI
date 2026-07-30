# FairFed Baseline Status

## Status

Blocked for comparative-result generation.

The revision does not currently contain a faithfully reproduced FairFed
implementation from the primary paper. No custom fairness-weighting heuristic
is labeled `B5`, and no FairFed result rows are generated.

## Required Resolution

Before enabling B5:

1. pin the primary paper and any authoritative reference implementation;
2. transcribe the client-weighting equations and fairness-budget parameters;
3. document every deviation needed for binary tabular Adult/COMPAS tasks;
4. add manually verifiable weighting tests;
5. compare an implementation trace against the reference;
6. freeze the configuration before test-set evaluation.

The common baseline API raises an explicit error for `B5` until those steps are
complete. This blocker does not prevent B0-B4, B6, or B7 implementation and
testing.
