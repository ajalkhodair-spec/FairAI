# V2 Public Inputs

## Scaling

Accuracy and fairness values use nonnegative scaled integers. The scale is
recorded in `metrics.json`; the initial profile uses scale `1000`. Thresholds
are rounded with the same scale before circuit input generation.

## Ordered Fields

The V2 public binding contains:

1. scaled accuracy;
2. scaled DP gap;
3. scaled EO gap;
4. scaled equalized-odds gap;
5. scaled subgroup-accuracy gap;
6. scaled minimum accuracy;
7. four scaled maximum fairness gaps;
8. five binary enabled-metric mask values;
9. node ID;
10. round ID;
11. packed policy version;
12. nonce;
13. manifest digest field output;
14. metrics digest field output.

The generated verification-key metadata must freeze the exact snarkjs signal
order before contract integration.

## Policy Version

`MAJOR.MINOR.PATCH` is packed into a 64-bit integer:

```text
(major << 32) | (minor << 16) | patch
```

Each component is an unsigned 16-bit value.

## Digest Mapping

Artifacts use strict canonical JSON: UTF-8, lexicographically sorted object
keys, no insignificant whitespace, and only strings, booleans, integers, null,
lists, and string-keyed objects. Floating-point values are rejected; use scaled
integers or decimal strings.

For SHA-256 digest `d`, the circuit field value is:

```text
int(d, 16) mod r
```

where the BN254 scalar field modulus is:

```text
21888242871839275222246405745257275088548364400416034343698204186575808495617
```

This is a deterministic field mapping. The circuit does not compute SHA-256.
