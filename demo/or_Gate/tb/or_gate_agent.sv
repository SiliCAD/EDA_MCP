// =============================================================================
// Class: or_gate_agent
// =============================================================================

class or_gate_agent extends uvm_agent;
    `uvm_component_utils(or_gate_agent)

    or_gate_driver    drv;
    or_gate_sequencer sqr;
    or_gate_monitor   mon;

    function new(string name = "or_gate_agent", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        mon = or_gate_monitor::type_id::create("mon", this);
        if (get_is_active() == UVM_ACTIVE) begin
            drv = or_gate_driver::type_id::create("drv", this);
            sqr = or_gate_sequencer::type_id::create("sqr", this);
        end
    endfunction

    function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        if (get_is_active() == UVM_ACTIVE) begin
            drv.seq_item_port.connect(sqr.seq_item_export);
        end
    endfunction

endclass : or_gate_agent
