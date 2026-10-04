// =============================================================================
// File: or_gate_sequence.sv
// Description: Directed, Random, and Exhaustive sequences for or_gate.
// =============================================================================

// Base sequence
class or_gate_base_sequence extends uvm_sequence #(or_gate_seq_item);
    `uvm_object_utils(or_gate_base_sequence)
    function new(string name = "or_gate_base_sequence");
        super.new(name);
    endfunction
endclass

// 1. Exhaustive Truth Table Sequence (00, 01, 10, 11)
class or_gate_exhaustive_sequence extends or_gate_base_sequence;
    `uvm_object_utils(or_gate_exhaustive_sequence)

    function new(string name = "or_gate_exhaustive_sequence");
        super.new(name);
    endfunction

    task body();
        or_gate_seq_item item;
        bit [1:0] truth_table[4] = '{2'b00, 2'b01, 2'b10, 2'b11};

        `uvm_info(get_type_name(), "Starting Exhaustive Truth Table Sequence", UVM_LOW)

        for (int i = 0; i < 4; i++) begin
            item = or_gate_seq_item::type_id::create("item");
            start_item(item);
            item.a = truth_table[i][1];
            item.b = truth_table[i][0];
            finish_item(item);
        end
    endtask
endclass

// 2. Constrained Random Sequence
class or_gate_random_sequence extends or_gate_base_sequence;
    `uvm_object_utils(or_gate_random_sequence)

    int num_txns = 50;

    function new(string name = "or_gate_random_sequence");
        super.new(name);
    endfunction

    task body();
        or_gate_seq_item item;
        `uvm_info(get_type_name(), $sformatf("Starting Random Sequence with %0d transactions", num_txns), UVM_LOW)

        repeat (num_txns) begin
            item = or_gate_seq_item::type_id::create("item");
            start_item(item);
            if (!item.randomize()) begin
                `uvm_fatal("RND_FAIL", "Randomization failed for seq_item!")
            end
            finish_item(item);
        end
    endtask
endclass

// 3. Toggle Sequence (stressing transitions 0->1 and 1->0)
class or_gate_toggle_sequence extends or_gate_base_sequence;
    `uvm_object_utils(or_gate_toggle_sequence)

    function new(string name = "or_gate_toggle_sequence");
        super.new(name);
    endfunction

    task body();
        or_gate_seq_item item;
        // Alternating patterns to force full toggle coverage
        bit [1:0] pattern[8] = '{2'b00, 2'b11, 2'b00, 2'b01, 2'b10, 2'b00, 2'b11, 2'b00};

        `uvm_info(get_type_name(), "Starting Toggle Sequence", UVM_LOW)

        for (int i = 0; i < 8; i++) begin
            item = or_gate_seq_item::type_id::create("item");
            start_item(item);
            item.a = pattern[i][1];
            item.b = pattern[i][0];
            finish_item(item);
        end
    endtask
endclass
