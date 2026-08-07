# COMPAS Dataset Card

## Source and Terms

- Source: ProPublica `compas-analysis`
- Pinned source commit:
  `bafff5da3f2e45eca6c2d5055faad269defd135a`
- File: `compas-scores-two-years.csv`
- SHA-256:
  `c451db85908b2f7fef1d83203bedf6b71ecda0d5af468d82ae62178f91d0cc7d`

The source repository does not contain an explicit dataset license. FairAI does
not redistribute the raw file. The downloader fetches it from the pinned
ProPublica source. ProPublica's published data terms require attribution and
prohibit republication of the raw data in full on a standalone basis.

## Task and Groups

- Target: two-year recidivism
- Favorable label: no recidivism within two years
- Primary protected attribute: race
- Privileged group: Caucasian
- Unprivileged group: African-American
- Supplementary protected attribute: sex

Race and sex are retained for fairness evaluation and excluded from predictive
features by default.

## Preparation

The loader applies the exclusions documented by ProPublica's two-year analysis:

- screening arrest difference between -30 and 30 days;
- `is_recid != -1`;
- charge degree is not `O`;
- score text is not `N/A`.

The primary comparison scope is restricted to African-American and Caucasian
records. The selected model features are age, age category, juvenile history,
prior count, and charge degree. Fixed train/validation/test splits use joint
label/race stratification. Encoders and scalers are fit only on training data.

This dataset contains criminal-justice records and known measurement and
matching limitations. Results must not be interpreted as ground truth about
individual risk or moral worth.

