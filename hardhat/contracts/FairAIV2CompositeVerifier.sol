// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./FairAISignedVerifierV2.sol";
import "./FairnessEligibilityV2Groth16Verifier.sol";

contract FairAIV2CompositeVerifier {
    uint256 private constant SNARK_SCALAR_FIELD =
        21888242871839275222246405745257275088548364400416034343698204186575808495617;

    FairnessEligibilityV2Groth16Verifier public immutable groth16Verifier;
    FairAISignedVerifierV2 public immutable signedVerifier;

    error InvalidPublicSignals();
    error DecisionBindingMismatch();

    constructor(address groth16Verifier_, address signedVerifier_) {
        require(groth16Verifier_ != address(0), "Groth16 verifier required");
        require(signedVerifier_ != address(0), "signed verifier required");
        groth16Verifier = FairnessEligibilityV2Groth16Verifier(groth16Verifier_);
        signedVerifier = FairAISignedVerifierV2(signedVerifier_);
    }

    function verifyProof(
        bytes calldata proof,
        uint256[] calldata publicSignals
    ) external returns (bool) {
        if (publicSignals.length != 21) revert InvalidPublicSignals();
        (
            uint256[2] memory pA,
            uint256[2][2] memory pB,
            uint256[2] memory pC,
            FairAISignedVerifierV2.Decision memory decision,
            bytes memory signature
        ) = abi.decode(
                proof,
                (
                    uint256[2],
                    uint256[2][2],
                    uint256[2],
                    FairAISignedVerifierV2.Decision,
                    bytes
                )
            );

        uint256[21] memory fixedSignals;
        for (uint256 i = 0; i < 21; i++) fixedSignals[i] = publicSignals[i];
        bool groth16Valid = groth16Verifier.verifyProof(pA, pB, pC, fixedSignals);
        if (
            publicSignals[17] != uint256(decision.nodeId) ||
            publicSignals[18] != decision.roundId ||
            publicSignals[19] != decision.policyVersion ||
            publicSignals[20] != decision.nonce ||
            publicSignals[0] != uint256(decision.manifestHash) % SNARK_SCALAR_FIELD ||
            publicSignals[1] != uint256(decision.metricsHash) % SNARK_SCALAR_FIELD ||
            decision.proofVerified != groth16Valid ||
            decision.policyPassed != groth16Valid ||
            decision.decision != groth16Valid
        ) revert DecisionBindingMismatch();

        bool signedApproved = signedVerifier.verifyDecision(decision, signature);
        return groth16Valid && signedApproved;
    }
}
