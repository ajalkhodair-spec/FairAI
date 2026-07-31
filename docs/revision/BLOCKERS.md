# Major Revision Blockers

The canonical blocker register is the repository-root `BLOCKERS.md`. Its stable
IDs are `BLK-001` through `BLK-004`; generated missing-data tables and workbook
rows reference those IDs.

The submitted-state tag gap remains documented in
`docs/revision/submitted_tag_gap.md` but does not block regression execution.
The four active blockers are:

- `BLK-001`: Circom 2.1.6, Powers of Tau, and V2 artifacts;
- `BLK-002`: Docker socket access for strict two-peer Kubo measurements;
- `BLK-003`: faithful FairFed implementation and reference tests;
- `BLK-004`: revision remote, anonymous public access, push, and release.
