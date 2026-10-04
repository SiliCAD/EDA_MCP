// =============================================================================
// Package: or_gate_tb_pkg
// =============================================================================

package or_gate_tb_pkg;
    import uvm_pkg::*;
    `include "uvm_macros.svh"

    `include "or_gate_seq_item.sv"
    `include "or_gate_sequencer.sv"
    `include "or_gate_driver.sv"
    `include "or_gate_monitor.sv"
    `include "or_gate_ref_model.sv"
    `include "or_gate_scoreboard.sv"
    `include "or_gate_coverage.sv"
    `include "or_gate_agent.sv"
    `include "or_gate_env_cfg.sv"
    `include "or_gate_env.sv"
    `include "or_gate_virtual_sequencer.sv"
    `include "or_gate_virtual_sequence.sv"
endpackage : or_gate_tb_pkg
