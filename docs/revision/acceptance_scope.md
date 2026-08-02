# Acceptance-Oriented Upgrade Scope

## Basis

This scope is derived from the editor decision, the three reviewer reports, and
the submitted 23-page manuscript. The larger master prompt is an upper-bound
design reference, not an implementation checklist.

## Mandatory Evidence

1. Preserve the submitted and current measured evidence under immutable hashes.
2. Complete the missing blockchain/IPFS ablation and one established fair-FL
   baseline on paired real-data configurations.
3. Measure robust approved-only aggregation under the declared poisoning cases.
4. Generate and verify the V2 proof with a reproducible research-only setup, or
   retain an exact blocker after a documented attempt.
5. Report signed-verifier trust, replay, revocation, compromise, and a bounded
   decentralized-verifier comparison.
6. Measure real multi-peer Kubo overhead, availability, and recovery.
7. Run a bounded multi-host full FairAI path on Adult and COMPAS.
8. Preserve bounded claims for privacy, ethics, robustness, scalability, and
   proof semantics.
9. Publish an anonymously accessible, clean-clone reproducible repository.
10. Map every response to code, configuration, raw evidence, statistics, and a
    manuscript change.

## Azure Boundary

Azure is used only where independent hosts and real network behavior improve
reviewer evidence. The default topology is three to five non-burstable Linux
VMs with isolated containers. Seven always-on VMs, Besu QBFT, Chaos Studio, and
large factorial experiments are optional unless a smaller deployment cannot
answer a reviewer concern.

Logical client count and physical host count are reported separately. Primary
algorithmic evaluation may use 3, 5, 10, 20, and 50 logical clients locally.
The complete Azure path targets 5, 10, and 20 logical clients across multiple
hosts; a 50-client Azure execution is an optional stress test.

## Explicit Nonclaims

- Azure execution is not production validation.
- Raw-data locality is not formal privacy.
- Threshold proofs over supplied metrics do not prove correct metric derivation.
- Approval gating does not universally detect poisoning.
- Local Hardhat or Azure Besu performance is not public-chain performance.
- Fairness is the directly operationalized ethical dimension; broader ethics
  remain governance properties, assumptions, extensions, or outside scope.
