# Major Revision Blockers

The canonical blocker register is the repository-root `BLOCKERS.md`. Its stable
IDs are `BLK-001` through `BLK-004`; generated missing-data tables and workbook
rows reference those IDs.

The submitted-state tag gap remains documented in
`docs/revision/submitted_tag_gap.md` but does not block regression execution.
The register contains two resolved and two active blockers:

- `BLK-001`: resolved with pinned and verified V2 artifacts and measurements;
- `BLK-002`: Docker socket access for strict two-peer Kubo measurements;
- `BLK-003`: resolved with the published FairFed server rule and tests;
- `BLK-004`: revision remote, anonymous public access, push, and release.
