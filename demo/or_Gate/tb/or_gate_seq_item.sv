// =============================================================================
// Class: or_gate_seq_item
// Description: UVM sequence item capturing inputs and observed response.
// =============================================================================

class or_gate_seq_item extends uvm_sequence_item;
    rand bit a;
    rand bit b;
    bit      out;

    `uvm_object_utils_begin(or_gate_seq_item)
        `uvm_field_int(a,   UVM_ALL_ON | UVM_BIN)
        `uvm_field_int(b,   UVM_ALL_ON | UVM_BIN)
        `uvm_field_int(out, UVM_ALL_ON | UVM_BIN)
    `uvm_object_utils_end

    function new(string name = "or_gate_seq_item");
        super.new(name);
    endfunction

    function string convert2string();
        return $sformatf("a=%b b=%b | out=%b", a, b, out);
    endfunction

endclass : or_gate_seq_item
