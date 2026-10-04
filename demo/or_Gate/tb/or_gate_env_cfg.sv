// =============================================================================
// Class: or_gate_env_cfg
// =============================================================================

class or_gate_env_cfg extends uvm_object;
    `uvm_object_utils(or_gate_env_cfg)

    bit has_scoreboard = 1;
    bit has_coverage   = 1;
    uvm_active_passive_enum is_active = UVM_ACTIVE;

    function new(string name = "or_gate_env_cfg");
        super.new(name);
    endfunction
endclass : or_gate_env_cfg
