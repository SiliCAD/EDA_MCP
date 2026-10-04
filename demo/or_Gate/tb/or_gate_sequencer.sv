// =============================================================================
// Class: or_gate_sequencer
// =============================================================================

class or_gate_sequencer extends uvm_sequencer #(or_gate_seq_item);
    `uvm_component_utils(or_gate_sequencer)

    function new(string name = "or_gate_sequencer", uvm_component parent = null);
        super.new(name, parent);
    endfunction
endclass : or_gate_sequencer
