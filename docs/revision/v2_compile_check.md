# V2 Circuit Compilation Check

The PATH-provided `circom` is version 0.5.46. A separate local source build at
tag `v2.1.9` was discovered and used only to check V2 source compatibility.

Command:

```sh
circom circuits/FairnessEligibilityV2.circom \
  --r1cs --wasm --sym \
  -o /tmp/fairai-v2-compile
snarkjs r1cs info /tmp/fairai-v2-compile/FairnessEligibilityV2.r1cs
```

Observed structure:

- non-linear constraints: 751;
- wires: 744;
- public inputs: 19;
- private inputs: 2;
- public outputs: 2.

SHA-256:

- V2 source:
  `99fe2e2486609eb46b2c9fe12f27771652fd0aac6eb316900898c9f8799ffec8`
- Circom 2.1.9 binary:
  `b5f02111ffb1e029ba438fe5585e6f5a5e7604020e967b888745dcfe72ffb112`
- generated R1CS:
  `83ec918529e053375fa2c9866a84f6bc09cfd7a0b36a0bb5f7443978e81eeb89`
- generated WASM:
  `76d7c7f9f28569eec5c038393a1aa253ad361d3d4cbd9b98c8e6c4865f57ac1c`

The generated files remain temporary and untracked. This check does not prove
the artifact manifest's Circom 2.1.6 declaration and does not replace trusted
setup, ZKey verification, proof generation, or the 30-repetition proof
benchmark. It removes only uncertainty that the checked V2 source can compile
under a compatible Circom 2 compiler.
