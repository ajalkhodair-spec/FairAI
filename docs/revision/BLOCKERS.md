# Major Revision Blockers

The canonical blocker register is the repository-root `BLOCKERS.md`. Its stable
IDs are `BLK-001` through `BLK-005`; generated missing-data tables and workbook
rows reference those IDs.

The submitted-state tag gap remains documented in
`docs/revision/submitted_tag_gap.md` but does not block regression execution.
The register contains four resolved or bounded-resolved historical blockers
and one open publication-provenance blocker:

- `BLK-001`: resolved with pinned and verified V2 artifacts and measurements;
- `BLK-002`: resolved for local native Kubo performance evidence and public
  clean-clone Docker Compose functional integration; consumer outage, WAN, and
  multi-host behavior remain limitations;
- `BLK-003`: resolved with the published FairFed server rule and tests;
- `BLK-004`: resolved with a public repository, passing GitHub Actions, an
  anonymous exact-pinned clean-clone test, GitHub release `v0.3.0`, and Zenodo
  version DOI `10.5281/zenodo.21864931`.
- `BLK-005`: open until the Circom 2.1.6 artifact-manifest declaration is
  reconciled with historical and current `0.5.46` executable metadata.

This file is a secondary view. Current publication-closure discrepancies are
recorded in `audits/prechange/evidence_discrepancy_report.md` and must not be
duplicated as independently maintained blocker entries here.
