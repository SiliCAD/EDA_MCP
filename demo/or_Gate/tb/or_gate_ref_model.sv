// =============================================================================
// Class: or_gate_ref_model
// Description: Independent golden model calculating expected OR logic.
// =============================================================================

class or_gate_ref_model extends uvm_component;
    `uvm_component_utils(or_gate_ref_model)

    uvm_analysis_port #(or_gate_seq_item) ap;

    function new(string name = "or_gate_ref_model", uvm_component parent = null);
        super.new(name, parent);
        ap = new("ap", this);
    endfunction

    // Predict golden response independently
    function bit predict(bit a, bit b);
        return a | b;
    endfunction

    function void process_item(or_gate_seq_item in_item);
        or_gate_seq_item exp_item;
        exp_item = or_gate_seq_item::type_id::create("exp_item");
        exp_item.a   = in_item.a;
        exp_item.b   = in_item.b;
        exp_item.out = predict(in_item.a, in_item.b);
        ap.write(exp_item);
    endfunction

endclass : or_gate_ref_model
