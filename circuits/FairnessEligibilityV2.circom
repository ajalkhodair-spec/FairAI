pragma circom 2.1.6;

template Num2Bits(n) {
    signal input in;
    signal output out[n];
    var reconstructed = 0;

    for (var i = 0; i < n; i++) {
        out[i] <-- (in >> i) & 1;
        out[i] * (out[i] - 1) === 0;
        reconstructed += out[i] * (1 << i);
    }
    reconstructed === in;
}

template LessThan(n) {
    signal input in[2];
    signal output out;
    component bits = Num2Bits(n + 1);
    bits.in <== in[0] + (1 << n) - in[1];
    out <== 1 - bits.out[n];
}

template LessEqThan(n) {
    signal input in[2];
    signal output out;
    component check = LessThan(n);
    check.in[0] <== in[0];
    check.in[1] <== in[1] + 1;
    out <== check.out;
}

template EnabledMaximum(bits) {
    signal input value;
    signal input maximum;
    signal input enabled;

    enabled * (enabled - 1) === 0;
    component check = LessEqThan(bits);
    check.in[0] <== value;
    check.in[1] <== maximum;
    enabled * (1 - check.out) === 0;
}

template EnabledMinimum(bits) {
    signal input value;
    signal input minimum;
    signal input enabled;

    enabled * (enabled - 1) === 0;
    component check = LessEqThan(bits);
    check.in[0] <== minimum;
    check.in[1] <== value;
    enabled * (1 - check.out) === 0;
}

template FairnessEligibilityV2(metricBits, identityBits) {
    signal input accuracy;
    signal input demographicParityGap;
    signal input equalOpportunityGap;
    signal input equalizedOddsGap;
    signal input subgroupAccuracyGap;

    signal input minimumAccuracy;
    signal input maximumDemographicParityGap;
    signal input maximumEqualOpportunityGap;
    signal input maximumEqualizedOddsGap;
    signal input maximumSubgroupAccuracyGap;

    signal input enableAccuracy;
    signal input enableDemographicParity;
    signal input enableEqualOpportunity;
    signal input enableEqualizedOdds;
    signal input enableSubgroupAccuracy;

    signal input nodeId;
    signal input roundId;
    signal input policyVersion;
    signal input nonce;
    signal input manifestDigestFieldIn;
    signal input metricsDigestFieldIn;
    signal output manifestDigestField;
    signal output metricsDigestField;

    component metricRanges[10];
    metricRanges[0] = Num2Bits(metricBits);
    metricRanges[0].in <== accuracy;
    metricRanges[1] = Num2Bits(metricBits);
    metricRanges[1].in <== demographicParityGap;
    metricRanges[2] = Num2Bits(metricBits);
    metricRanges[2].in <== equalOpportunityGap;
    metricRanges[3] = Num2Bits(metricBits);
    metricRanges[3].in <== equalizedOddsGap;
    metricRanges[4] = Num2Bits(metricBits);
    metricRanges[4].in <== subgroupAccuracyGap;
    metricRanges[5] = Num2Bits(metricBits);
    metricRanges[5].in <== minimumAccuracy;
    metricRanges[6] = Num2Bits(metricBits);
    metricRanges[6].in <== maximumDemographicParityGap;
    metricRanges[7] = Num2Bits(metricBits);
    metricRanges[7].in <== maximumEqualOpportunityGap;
    metricRanges[8] = Num2Bits(metricBits);
    metricRanges[8].in <== maximumEqualizedOddsGap;
    metricRanges[9] = Num2Bits(metricBits);
    metricRanges[9].in <== maximumSubgroupAccuracyGap;

    component identityRanges[4];
    identityRanges[0] = Num2Bits(identityBits);
    identityRanges[0].in <== nodeId;
    identityRanges[1] = Num2Bits(identityBits);
    identityRanges[1].in <== roundId;
    identityRanges[2] = Num2Bits(identityBits);
    identityRanges[2].in <== policyVersion;
    identityRanges[3] = Num2Bits(identityBits);
    identityRanges[3].in <== nonce;

    component accuracyCheck = EnabledMinimum(metricBits);
    accuracyCheck.value <== accuracy;
    accuracyCheck.minimum <== minimumAccuracy;
    accuracyCheck.enabled <== enableAccuracy;

    component dpCheck = EnabledMaximum(metricBits);
    dpCheck.value <== demographicParityGap;
    dpCheck.maximum <== maximumDemographicParityGap;
    dpCheck.enabled <== enableDemographicParity;

    component eoCheck = EnabledMaximum(metricBits);
    eoCheck.value <== equalOpportunityGap;
    eoCheck.maximum <== maximumEqualOpportunityGap;
    eoCheck.enabled <== enableEqualOpportunity;

    component eOddsCheck = EnabledMaximum(metricBits);
    eOddsCheck.value <== equalizedOddsGap;
    eOddsCheck.maximum <== maximumEqualizedOddsGap;
    eOddsCheck.enabled <== enableEqualizedOdds;

    component sagCheck = EnabledMaximum(metricBits);
    sagCheck.value <== subgroupAccuracyGap;
    sagCheck.maximum <== maximumSubgroupAccuracyGap;
    sagCheck.enabled <== enableSubgroupAccuracy;

    // Digest fields are public bindings. SHA-256 is recomputed by the
    // off-circuit verifier and is not computed inside this circuit.
    manifestDigestField <== manifestDigestFieldIn;
    metricsDigestField <== metricsDigestFieldIn;
}

component main {public [
    accuracy,
    demographicParityGap,
    equalOpportunityGap,
    equalizedOddsGap,
    subgroupAccuracyGap,
    minimumAccuracy,
    maximumDemographicParityGap,
    maximumEqualOpportunityGap,
    maximumEqualizedOddsGap,
    maximumSubgroupAccuracyGap,
    enableAccuracy,
    enableDemographicParity,
    enableEqualOpportunity,
    enableEqualizedOdds,
    enableSubgroupAccuracy,
    nodeId,
    roundId,
    policyVersion,
    nonce
]} = FairnessEligibilityV2(32, 64);
