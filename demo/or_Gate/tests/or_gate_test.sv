// =============================================================================
// File: or_gate_test.sv
// Description: UVM test classes for or_gate.
// =============================================================================

package or_gate_test_pkg;
    import uvm_pkg::*;
    `include "uvm_macros.svh"
    import or_gate_tb_pkg::*;
    `include "or_gate_sequence.sv"

    // Base Test
    class or_gate_base_test extends uvm_test;
        `uvm_component_utils(or_gate_base_test)

        or_gate_env env;

        function new(string name = "or_gate_base_test", uvm_component parent = null);
            super.new(name, parent);
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);
            env = or_gate_env::type_id::create("env", this);
        endfunction

        function void end_of_elaboration_phase(uvm_phase phase);
            super.end_of_elaboration_phase(phase);
            uvm_top.print_topology();
        endfunction
    endclass

    // 1. Directed Exhaustive Test
    class or_gate_exhaustive_test extends or_gate_base_test;
        `uvm_component_utils(or_gate_exhaustive_test)

        function new(string name = "or_gate_exhaustive_test", uvm_component parent = null);
            super.new(name, parent);
        endfunction

        task run_phase(uvm_phase phase);
            or_gate_exhaustive_sequence seq;
            phase.raise_objection(this);
            seq = or_gate_exhaustive_sequence::type_id::create("seq");
            seq.start(env.agt.sqr);
            #20ns;
            phase.drop_objection(this);
        endtask
    endclass

    // 2. Random Test
    class or_gate_random_test extends or_gate_base_test;
        `uvm_component_utils(or_gate_random_test)

        function new(string name = "or_gate_random_test", uvm_component parent = null);
            super.new(name, parent);
        endfunction

        task run_phase(uvm_phase phase);
            or_gate_random_sequence seq;
            phase.raise_objection(this);
            seq = or_gate_random_sequence::type_id::create("seq");
            seq.num_txns = 100;
            seq.start(env.agt.sqr);
            #20ns;
            phase.drop_objection(this);
        endtask
    endclass

    // 3. Toggle & Corner Test
    class or_gate_corner_test extends or_gate_base_test;
        `uvm_component_utils(or_gate_corner_test)

        function new(string name = "or_gate_corner_test", uvm_component parent = null);
            super.new(name, parent);
        endfunction

        task run_phase(uvm_phase phase);
            or_gate_toggle_sequence seq;
            phase.raise_objection(this);
            seq = or_gate_toggle_sequence::type_id::create("seq");
            seq.start(env.agt.sqr);
            #20ns;
            phase.drop_objection(this);
        endtask
    endclass

endpackage : or_gate_test_pkg
