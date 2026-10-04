// =============================================================================
// Class: or_gate_scoreboard
// Description: Lockstep per-operation scoreboard verifying actual vs expected.
// =============================================================================

`uvm_analysis_imp_decl(_mon)

class or_gate_scoreboard extends uvm_scoreboard;
    `uvm_component_utils(or_gate_scoreboard)

    uvm_analysis_imp_mon #(or_gate_seq_item, or_gate_scoreboard) aport_mon;
    or_gate_ref_model ref_model;

    int unsigned vector_count;
    int unsigned pass_count;
    int unsigned error_count;

    function new(string name = "or_gate_scoreboard", uvm_component parent = null);
        super.new(name, parent);
        vector_count = 0;
        pass_count   = 0;
        error_count  = 0;
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        aport_mon = new("aport_mon", this);
        ref_model = or_gate_ref_model::type_id::create("ref_model", this);
    endfunction

    function void write_mon(or_gate_seq_item actual_item);
        bit expected_out;
        expected_out = ref_model.predict(actual_item.a, actual_item.b);
        vector_count++;

        if (actual_item.out === expected_out) begin
            pass_count++;
            `uvm_info("SCOREBOARD_PASS", $sformatf("MATCH [#%0d]: a=%0b b=%0b | actual=%0b expected=%0b",
                      vector_count, actual_item.a, actual_item.b, actual_item.out, expected_out), UVM_HIGH)
        end else begin
            error_count++;
            `uvm_error("SCOREBOARD_MISMATCH", $sformatf("MISMATCH [#%0d]: a=%0b b=%0b | actual=%0b expected=%0b",
                       vector_count, actual_item.a, actual_item.b, actual_item.out, expected_out))
        end
    endfunction

    function void report_phase(uvm_phase phase);
        super.report_phase(phase);
        `uvm_info("SCOREBOARD_SUMMARY", "--------------------------------------------------", UVM_LOW)
        `uvm_info("SCOREBOARD_SUMMARY", $sformatf("Total Vectors Checked : %0d", vector_count), UVM_LOW)
        `uvm_info("SCOREBOARD_SUMMARY", $sformatf("Total Passed          : %0d", pass_count), UVM_LOW)
        `uvm_info("SCOREBOARD_SUMMARY", $sformatf("Total Errors          : %0d", error_count), UVM_LOW)
        `uvm_info("SCOREBOARD_SUMMARY", "--------------------------------------------------", UVM_LOW)

        if (error_count > 0 || vector_count == 0) begin
            `uvm_fatal("SCOREBOARD_FAIL", "*** VERIFICATION FAILED - SCOREBOARD ERRORS DETECTED ***")
        end else begin
            `uvm_info("SCOREBOARD_PASS", "*** VERIFICATION PASSED - 100% SCOREBOARD CONFORMANCE ***", UVM_LOW)
        end
    endfunction

endclass : or_gate_scoreboard
