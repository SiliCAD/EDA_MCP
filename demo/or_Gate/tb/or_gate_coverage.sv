// =============================================================================
// Class: or_gate_coverage
// Description: Comprehensive functional coverage subscriber with crosses and transitions.
// =============================================================================

class or_gate_coverage extends uvm_subscriber #(or_gate_seq_item);
    `uvm_component_utils(or_gate_coverage)

    or_gate_seq_item tr;
    real cur_cov;

    covergroup cg_or;
        option.per_instance = 1;
        option.comment = "or_gate functional coverage";

        cp_a: coverpoint tr.a {
            bins zero = {1'b0};
            bins one  = {1'b1};
            bins trans_0_to_1 = (1'b0 => 1'b1);
            bins trans_1_to_0 = (1'b1 => 1'b0);
        }

        cp_b: coverpoint tr.b {
            bins zero = {1'b0};
            bins one  = {1'b1};
            bins trans_0_to_1 = (1'b0 => 1'b1);
            bins trans_1_to_0 = (1'b1 => 1'b0);
        }

        cp_out: coverpoint tr.out {
            bins zero = {1'b0};
            bins one  = {1'b1};
            bins trans_0_to_1 = (1'b0 => 1'b1);
            bins trans_1_to_0 = (1'b1 => 1'b0);
        }

        // Exhaustive input cross coverage: 00, 01, 10, 11 (including transition dynamics)
        cross_inputs: cross cp_a, cp_b;

        // Dedicated value coverpoints for input-to-output truth table mapping
        cp_a_val: coverpoint tr.a {
            bins zero = {1'b0};
            bins one  = {1'b1};
        }

        cp_b_val: coverpoint tr.b {
            bins zero = {1'b0};
            bins one  = {1'b1};
        }

        cp_out_val: coverpoint tr.out {
            bins zero = {1'b0};
            bins one  = {1'b1};
        }

        // Input to output mapping cross with impossible bins ignored
        cross_a_out: cross cp_a_val, cp_out_val {
            ignore_bins unreach_a1_out0 = binsof(cp_a_val.one) && binsof(cp_out_val.zero);
        }

        cross_b_out: cross cp_b_val, cp_out_val {
            ignore_bins unreach_b1_out0 = binsof(cp_b_val.one) && binsof(cp_out_val.zero);
        }

    endgroup : cg_or

    function new(string name = "or_gate_coverage", uvm_component parent = null);
        super.new(name, parent);
        cg_or = new();
        cur_cov = 0.0;
    endfunction

    function void write(or_gate_seq_item t);
        tr = t;
        cg_or.sample();
        cur_cov = cg_or.get_coverage();
    endfunction

    function real get_cov();
        return cg_or.get_coverage();
    endfunction

    function void report_phase(uvm_phase phase);
        super.report_phase(phase);
        cur_cov = cg_or.get_coverage();
        `uvm_info("COVERAGE_REPORT", $sformatf("Overall Functional Coverage: %0.2f%%", cur_cov), UVM_LOW)
    endfunction

endclass : or_gate_coverage
