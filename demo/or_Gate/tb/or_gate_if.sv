// =============================================================================
// Interface: or_gate_if
// Description: Physical interface and synchronous sample strobes for or_gate.
// =============================================================================

interface or_gate_if (input logic clk);
    logic a = 1'b0;
    logic b = 1'b0;
    logic out;

    // Clocking block for driver
    clocking drv_cb @(posedge clk);
        default input #1step output #1ns;
        output a;
        output b;
        input  out;
    endclocking

    // Clocking block for monitor (sampled after non-blocking delta)
    clocking mon_cb @(posedge clk);
        default input #1step;
        input a;
        input b;
        input out;
    endclocking

    modport DRV (clocking drv_cb);
    modport MON (clocking mon_cb);

endinterface : or_gate_if
