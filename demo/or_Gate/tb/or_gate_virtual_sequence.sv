// =============================================================================
// Class: or_gate_virtual_sequence
// =============================================================================

class or_gate_virtual_sequence extends uvm_sequence;
    `uvm_object_utils(or_gate_virtual_sequence)
    `uvm_declare_p_sequencer(or_gate_virtual_sequencer)

    function new(string name = "or_gate_virtual_sequence");
        super.new(name);
    endfunction
endclass : or_gate_virtual_sequence
