// =============================================================================
// Class: or_gate_virtual_sequencer
// =============================================================================

class or_gate_virtual_sequencer extends uvm_sequencer;
    `uvm_component_utils(or_gate_virtual_sequencer)

    or_gate_sequencer sqr;

    function new(string name = "or_gate_virtual_sequencer", uvm_component parent = null);
        super.new(name, parent);
    endfunction
endclass : or_gate_virtual_sequencer
