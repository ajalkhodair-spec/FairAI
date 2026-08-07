# Major Revision Blockers

The canonical blocker register is the repository-root `BLOCKERS.md`. Its stable
IDs are `BLK-001` through `BLK-004`; generated missing-data tables and workbook
rows reference those IDs.

The submitted-state tag gap remains documented in
`docs/revision/submitted_tag_gap.md` but does not block regression execution.
The register contains four resolved or bounded-resolved blockers:

- `BLK-001`: resolved with pinned and verified V2 artifacts and measurements;
- `BLK-002`: resolved for local native Kubo; Docker Compose, recovery, and
  multi-host behavior remain limitations;
- `BLK-003`: resolved with the published FairFed server rule and tests;
- `BLK-004`: resolved with a public revision branch, passing GitHub Actions,
  and an anonymous clean-clone test; the release tag and archival DOI remain
  post-merge publication actions.
