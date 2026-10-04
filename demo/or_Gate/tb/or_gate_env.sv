// =============================================================================
// Class: or_gate_env
// =============================================================================

class or_gate_env extends uvm_env;
    `uvm_component_utils(or_gate_env)

    or_gate_agent      agt;
    or_gate_scoreboard scb;
    or_gate_coverage   cov;
    or_gate_env_cfg    cfg;

    function new(string name = "or_gate_env", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if (!uvm_config_db#(or_gate_env_cfg)::get(this, "", "cfg", cfg)) begin
            cfg = or_gate_env_cfg::type_id::create("cfg");
        end

        agt = or_gate_agent::type_id::create("agt", this);
        agt.is_active = cfg.is_active;

        if (cfg.has_scoreboard) begin
            scb = or_gate_scoreboard::type_id::create("scb", this);
        end

        if (cfg.has_coverage) begin
            cov = or_gate_coverage::type_id::create("cov", this);
        end
    endfunction

    function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        if (cfg.has_scoreboard) begin
            agt.mon.ap.connect(scb.aport_mon);
        end
        if (cfg.has_coverage) begin
            agt.mon.ap.connect(cov.analysis_export);
        end
    endfunction

endclass : or_gate_env
