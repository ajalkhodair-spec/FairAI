template Num2Bits(n) {
    signal input in;
    signal output out[n];
    var lc = 0;

    for (var i = 0; i < n; i++) {
        out[i] <-- (in >> i) & 1;
        out[i] * (out[i] - 1) === 0;
        lc += out[i] * (1 << i);
    }

    lc === in;
}

template LessThan(n) {
    signal input a;
    signal input b;
    signal output out;

    component n2b = Num2Bits(n + 1);
    n2b.in <== a + (1 << n) - b;
    out <== 1 - n2b.out[n];
}

template LessEqThan(n) {
    signal input a;
    signal input b;
    signal output out;

    component lt = LessThan(n);
    lt.a <== a;
    lt.b <== b + 1;
    out <== lt.out;
}

template FairnessEligibility(n) {
    signal input accuracy_in;
    signal input fairness_gap_in;
    signal input min_accuracy_in;
    signal input max_gap_in;
    signal input node_id_in;
    signal input round_id_in;

    signal output accuracy;
    signal output fairness_gap;
    signal output min_accuracy;
    signal output max_gap;
    signal output node_id;
    signal output round_id;

    accuracy <== accuracy_in;
    fairness_gap <== fairness_gap_in;
    min_accuracy <== min_accuracy_in;
    max_gap <== max_gap_in;
    node_id <== node_id_in;
    round_id <== round_id_in;

    component range_accuracy = Num2Bits(n);
    component range_gap = Num2Bits(n);
    component range_min_accuracy = Num2Bits(n);
    component range_max_gap = Num2Bits(n);
    component range_node = Num2Bits(n);
    component range_round = Num2Bits(n);

    range_accuracy.in <== accuracy_in;
    range_gap.in <== fairness_gap_in;
    range_min_accuracy.in <== min_accuracy_in;
    range_max_gap.in <== max_gap_in;
    range_node.in <== node_id_in;
    range_round.in <== round_id_in;

    component accuracy_ok = LessEqThan(n);
    accuracy_ok.a <== min_accuracy_in;
    accuracy_ok.b <== accuracy_in;
    accuracy_ok.out === 1;

    component fairness_ok = LessEqThan(n);
    fairness_ok.a <== fairness_gap_in;
    fairness_ok.b <== max_gap_in;
    fairness_ok.out === 1;
}

component main = FairnessEligibility(16);
