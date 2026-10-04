// =============================================================================
// Module: or_gate
// Description: Pure synthesizable 2-input OR gate (zero verification code).
// =============================================================================

module or_gate (
    input  wire a,
    input  wire b,
    output wire out
);

    // Combinational OR logic
    assign out = a | b;

endmodule
