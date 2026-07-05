// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract FairAIZKVerifierMock {
    enum SignalIndex {
        AccuracyScaled,
        DemographicParityGapScaled,
        MinAccuracyScaled,
        MaxGapScaled,
        Correct,
        Samples,
        Group0PredPositive,
        Group0Count,
        Group1PredPositive,
        Group1Count,
        NodeId,
        RoundId,
        ProofDigest
    }

    error InvalidPublicSignals();

    function verifyProof(
        bytes calldata proof,
        uint256[] calldata publicSignals
    ) external pure returns (bool) {
        if (publicSignals.length != 13) revert InvalidPublicSignals();
        if (proof.length == 0) return false;

        uint256 samples = publicSignals[uint256(SignalIndex.Samples)];
        uint256 group0Count = publicSignals[uint256(SignalIndex.Group0Count)];
        uint256 group1Count = publicSignals[uint256(SignalIndex.Group1Count)];
        uint256 correct = publicSignals[uint256(SignalIndex.Correct)];
        uint256 accuracy = publicSignals[uint256(SignalIndex.AccuracyScaled)];
        uint256 gap = publicSignals[uint256(SignalIndex.DemographicParityGapScaled)];
        uint256 minAccuracy = publicSignals[uint256(SignalIndex.MinAccuracyScaled)];
        uint256 maxGap = publicSignals[uint256(SignalIndex.MaxGapScaled)];
        uint256 proofDigest = publicSignals[uint256(SignalIndex.ProofDigest)];

        if (samples == 0 || group0Count + group1Count != samples) return false;
        if (correct > samples) return false;
        if (accuracy < minAccuracy || gap > maxGap) return false;
        if (uint256(sha256(proof)) != proofDigest) return false;
        return true;
    }
}
