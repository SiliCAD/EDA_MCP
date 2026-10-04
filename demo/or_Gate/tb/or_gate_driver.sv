// =============================================================================
// Class: or_gate_driver
// Description: Synchronous UVM driver driving DUT inputs.
// =============================================================================

class or_gate_driver extends uvm_driver #(or_gate_seq_item);
    `uvm_component_utils(or_gate_driver)

    virtual or_gate_if vif;

    function new(string name = "or_gate_driver", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if (!uvm_config_db#(virtual or_gate_if)::get(this, "", "vif", vif)) begin
            `uvm_fatal("NOVIF", $sformatf("Virtual interface or_gate_if not found in config_db!"))
        end
    endfunction

    task run_phase(uvm_phase phase);
        or_gate_seq_item req_item;
        // Initialize interface to inactive state
        vif.a <= 1'b0;
        vif.b <= 1'b0;

        forever begin
            seq_item_port.get_next_item(req_item);
            drive_item(req_item);
            seq_item_port.item_done();
        end
    endtask

    task drive_item(or_gate_seq_item item);
        @(posedge vif.clk);
        vif.a <= item.a;
        vif.b <= item.b;
        `uvm_info(get_type_name(), $sformatf("Driven: a=%0b, b=%0b", item.a, item.b), UVM_HIGH)
    endtask

endclass : or_gate_driver
