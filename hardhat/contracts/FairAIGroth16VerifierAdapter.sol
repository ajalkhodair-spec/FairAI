// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./FairnessEligibilityGroth16Verifier.sol";

contract FairAIGroth16VerifierAdapter {
    Groth16Verifier public immutable verifier;

    constructor(address verifier_) {
        require(verifier_ != address(0), "verifier required");
        verifier = Groth16Verifier(verifier_);
    }

    function verifyProof(
        bytes calldata proof,
        uint256[] calldata publicSignals
    ) external view returns (bool) {
        if (proof.length == 0 || publicSignals.length != 12) {
            return false;
        }

        (
            uint[2] memory pA,
            uint[2][2] memory pB,
            uint[2] memory pC
        ) = abi.decode(proof, (uint[2], uint[2][2], uint[2]));

        uint[12] memory fixedSignals;
        for (uint256 i = 0; i < 12; i++) {
            fixedSignals[i] = publicSignals[i];
        }

        return verifier.verifyProof(pA, pB, pC, fixedSignals);
    }
}
