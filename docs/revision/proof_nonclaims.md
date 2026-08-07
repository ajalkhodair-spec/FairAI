# V2 Proof Non-Claims

The V2 circuit does not prove:

- that fairness metrics were computed correctly from private records;
- that local data are authentic, complete, representative, or unmodified;
- that training was executed honestly;
- that the serialized model corresponds to the claimed training;
- that a local model is free from poisoning or backdoors;
- that protected attributes are correct;
- that SHA-256 was evaluated inside the circuit;
- that IPFS retained the artifacts;
- that a verifier signing key was uncompromised.

Artifact hashes are recomputed outside the circuit and compared with bound
public field elements. This gives artifact substitution detection under the
off-circuit verifier trust assumption; it does not convert supplied metrics
into privately recomputed metrics.
