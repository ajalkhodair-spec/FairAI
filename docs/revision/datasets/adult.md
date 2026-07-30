# Adult Census Income Dataset Card

## Source and License

- Source: UCI Machine Learning Repository, dataset ID 2
- DOI: `10.24432/C5XW20`
- Download: `https://archive.ics.uci.edu/static/public/2/adult.zip`
- License: CC BY 4.0
- Pinned archive SHA-256:
  `7537312dd56c2b98035880805ce99e68183a30ee468aa5329d6df0fbb3cc21bb`

## Task and Groups

- Target: income category
- Favorable label: income greater than USD 50,000
- Primary protected attribute: sex
- Privileged group: Male
- Unprivileged group: Female
- Supplementary protected attribute: race

Protected attributes are retained for fairness evaluation and excluded from
predictive features by default.

## Preparation

- Preserve UCI `adult.test` as the global test set.
- Split the official training file into training and validation subsets using a
  fixed seed and joint label/sex stratification.
- Remove rows containing the documented `?` missing marker.
- Fit numeric scaling and categorical encoding on training data only.
- Transform validation and test data with the training-fitted transformer.

The downloader verifies the archive checksum and records extracted-file hashes.
Raw files are excluded from Git.

