// =============================================================================
// Class: or_gate_monitor
// Description: Passive observer monitoring DUT interface transactions.
// =============================================================================

class or_gate_monitor extends uvm_monitor;
    `uvm_component_utils(or_gate_monitor)

    virtual or_gate_if vif;
    uvm_analysis_port #(or_gate_seq_item) ap;

    function new(string name = "or_gate_monitor", uvm_component parent = null);
        super.new(name, parent);
        ap = new("ap", this);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if (!uvm_config_db#(virtual or_gate_if)::get(this, "", "vif", vif)) begin
            `uvm_fatal("NOVIF", "Virtual interface or_gate_if not found in config_db!")
        end
    endfunction

    task run_phase(uvm_phase phase);
        or_gate_seq_item item;
        forever begin
            // Sample on negedge to ensure all combinational propagation has completed cleanly
            @(negedge vif.clk);
            item = or_gate_seq_item::type_id::create("item");
            item.a   = vif.a;
            item.b   = vif.b;
            item.out = vif.out;
            `uvm_info(get_type_name(), $sformatf("Monitored: %s", item.convert2string()), UVM_HIGH)
            ap.write(item);
        end
    endtask

endclass : or_gate_monitor
