# Manuscript Source Status

**Status:** `MANUSCRIPT_SOURCE_LOCATED_UNBOUND_TO_RELEASE`

## Located source

- Main TeX: external local source, now imported as `manuscript/FairAI.tex`
- TeX SHA-256: `edd73c6efae0d714c5419e590f4b773825bf59f6a01d6a14bb88a7ae54ca4555`
- Built PDF: external local build used only for checksum comparison
- PDF SHA-256: `af80081622a54421486b09c870d7595b67970861cfdde993abef132564771ee0`
- Local source ZIP: external local archive, not a publication artifact
- ZIP SHA-256: `f2938a84633b9f57bbaf7ac2e3e974a29276fd96f0d7605d8a77e0547849d5e8`

## Required components

| Component | Result |
|---|---|
| Main `.tex` source | Located |
| Bibliography source | Inline `thebibliography` block located |
| Journal class/template | `Definitions/mdpi.cls` and bibliography styles located |
| Figure sources | Located under `Figures/` and `Figures/Results/` |
| Table/result integration | Embedded in TeX; repository also contains generated LaTeX tables |
| Build evidence | Existing log reports successful 23-page PDF build |
| Explicit build instructions | Not located beside the manuscript source |
| Git/release binding | Missing |

## Findings

The editable manuscript prerequisite is satisfied locally. It is not satisfied
as a reproducible release artifact because the manuscript source, template, and
figures are outside the Git repository and absent from v0.2.1 and the Zenodo
software archive. The source ZIP also contains macOS metadata, build outputs,
and numerous empty `synctex(busy)` files, so it should not be adopted unchanged
as a canonical archival source package.

Manuscript editing is not blocked by source absence. Final scientific closure
is blocked until one canonical manuscript source package is versioned or bound
by checksum to the evidence state used for the revision.
