// =============================================================================
// Module: top
// Description: UVM top-level testbench instantiation with clock generation.
// =============================================================================

`timescale 1ns/1ps

module top;
    import uvm_pkg::*;
    `include "uvm_macros.svh"
    import or_gate_tb_pkg::*;
    import or_gate_test_pkg::*;

    // 100MHz Testbench Clock (10ns period)
    logic clk;
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    // Interface instantiation
    or_gate_if vif(clk);

    // DUT instantiation
    or_gate dut (
        .a(vif.a),
        .b(vif.b),
        .out(vif.out)
    );

    // Run test and setup waveform dumping
    initial begin
        // Set virtual interface in config_db
        uvm_config_db#(virtual or_gate_if)::set(null, "*", "vif", vif);

        // VCD dumping for debugging & dashboard inspection
        $dumpfile("dumpfile.vcd");
        $dumpvars(0, top);

        // Execute specified UVM test
        run_test();
    end

endmodule
