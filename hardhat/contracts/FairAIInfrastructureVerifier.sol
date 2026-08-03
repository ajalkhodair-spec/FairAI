// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Infrastructure-only verifier for the B2 no-policy/no-ZK baseline.
/// @dev This contract must never be used for B3, B4, or B7 approval decisions.
contract FairAIInfrastructureVerifier {
    function verifyProof(
        bytes calldata,
        uint256[] calldata
    ) external pure returns (bool) {
        return true;
    }
}
