# FairAI Manuscript Source

This directory is the canonical editable manuscript source for the reconciled
major-revision package. It contains the MDPI template files and all figures
referenced by `FairAI.tex`.

## Build

From this directory, run:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error FairAI.tex
```

If `latexmk` is unavailable, run `pdflatex` twice:

```bash
pdflatex -interaction=nonstopmode -halt-on-error FairAI.tex
pdflatex -interaction=nonstopmode -halt-on-error FairAI.tex
```

The bibliography is an inline `thebibliography` block, so no external BibTeX
database is required. Generated PDF, log, auxiliary, and SyncTeX files are
ignored and are not canonical source artifacts.

## Evidence boundary

Scientific tables and result claims must be traced to files under
`outputs/major_revision/` or `outputs/revision_audit/`. The repository baseline
and original local-source hashes are recorded in `SOURCE_PROVENANCE.md`.
