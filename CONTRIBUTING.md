# Contributing

1. Create a focused branch.
2. Keep generated evidence separate from source code.
3. Add or update tests for behavior changes.
4. Run `make test` and `make revision-smoke`.
5. Do not commit secrets, raw datasets, private keys, Powers of Tau files, or
   unreviewed ZKey material.
6. Label evidence as measured, derived, modeled, estimated, tested, blocked, or
   missing.
7. Never replace a blocked baseline or infrastructure path with a heuristic
   under the original name.
8. Include source paths and run manifests for result changes.

Security-sensitive contract, verifier, circuit, and canonicalization changes
require explicit negative tests and review of the threat assumptions.
