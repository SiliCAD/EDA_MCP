// =============================================================================
// Module: or_gate_assertions
// Description: SystemVerilog Assertions (SVA) and formal properties for or_gate.
//              Non-intrusively bound via SystemVerilog `bind` directive.
// =============================================================================

module or_gate_assertions (
    input wire a,
    input wire b,
    input wire out
);

    // -------------------------------------------------------------------------
    // Safety Properties (Assertions)
    // -------------------------------------------------------------------------

    // A1: Logic Truth Table - 00 -> 0
    property p_truth_00;
        @(a or b or out)
        disable iff ($time == 0 || $isunknown({a, b, out}))
        (!a && !b) |-> (out == 1'b0);
    endproperty
    assert_truth_00: assert property (p_truth_00)
        else $error("[SVA FAIL] or_gate: 0 | 0 produced 1'b1!");

    // A2: Logic Truth Table - 01 -> 1
    property p_truth_01;
        @(a or b or out)
        disable iff ($time == 0 || $isunknown({a, b, out}))
        (!a && b) |-> (out == 1'b1);
    endproperty
    assert_truth_01: assert property (p_truth_01)
        else $error("[SVA FAIL] or_gate: 0 | 1 produced 1'b0!");

    // A3: Logic Truth Table - 10 -> 1
    property p_truth_10;
        @(a or b or out)
        disable iff ($time == 0 || $isunknown({a, b, out}))
        (a && !b) |-> (out == 1'b1);
    endproperty
    assert_truth_10: assert property (p_truth_10)
        else $error("[SVA FAIL] or_gate: 1 | 0 produced 1'b0!");

    // A4: Logic Truth Table - 11 -> 1
    property p_truth_11;
        @(a or b or out)
        disable iff ($time == 0 || $isunknown({a, b, out}))
        (a && b) |-> (out == 1'b1);
    endproperty
    assert_truth_11: assert property (p_truth_11)
        else $error("[SVA FAIL] or_gate: 1 | 1 produced 1'b0!");

    // A5: Complete Functional Equivalence
    property p_functional_equivalence;
        @(a or b or out)
        disable iff ($time == 0 || $isunknown({a, b, out}))
        out == (a | b);
    endproperty
    assert_equiv: assert property (p_functional_equivalence)
        else $error("[SVA FAIL] or_gate: Functional mismatch with golden OR!");

    // A6: Output Dominance (Any 1 implies Output 1)
    property p_dominance_a;
        @(a or b or out)
        disable iff ($time == 0 || $isunknown({a, b, out}))
        a |-> (out == 1'b1);
    endproperty
    assert_dominance_a: assert property (p_dominance_a)
        else $error("[SVA FAIL] or_gate: a=1 did not force out=1!");

    property p_dominance_b;
        @(a or b or out)
        disable iff ($time == 0 || $isunknown({a, b, out}))
        b |-> (out == 1'b1);
    endproperty
    assert_dominance_b: assert property (p_dominance_b)
        else $error("[SVA FAIL] or_gate: b=1 did not force out=1!");

    // -------------------------------------------------------------------------
    // Liveness & Vacuity Properties (Covers)
    // -------------------------------------------------------------------------
    cover_case_00: cover property (@(a or b or out) disable iff ($time == 0 || $isunknown({a, b, out})) (!a && !b && !out));
    cover_case_01: cover property (@(a or b or out) disable iff ($time == 0 || $isunknown({a, b, out})) (!a && b && out));
    cover_case_10: cover property (@(a or b or out) disable iff ($time == 0 || $isunknown({a, b, out})) (a && !b && out));
    cover_case_11: cover property (@(a or b or out) disable iff ($time == 0 || $isunknown({a, b, out})) (a && b && out));

    cover_toggle_out_high: cover property (@(a or b or out) disable iff ($time == 0 || $isunknown({a, b, out})) (!out ##1 out));
    cover_toggle_out_low:  cover property (@(a or b or out) disable iff ($time == 0 || $isunknown({a, b, out})) (out ##1 !out));

endmodule

// Non-intrusive bind directive
bind or_gate or_gate_assertions u_or_gate_assertions (
    .a(a),
    .b(b),
    .out(out)
);
