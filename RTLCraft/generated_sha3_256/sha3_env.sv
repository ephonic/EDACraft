// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : sha3_env.sv
// Module Name : SHA3Env
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef SHA3ENV_SV
`define SHA3ENV_SV

import sha3_256_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class SHA3Env extends uvm_env;
    `uvm_component_utils(SHA3Env)

    SHA3Agent agent;
    SHA3Scoreboard sb;

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        agent = SHA3Agent::type_id::create("agent", this);
        sb = SHA3Scoreboard::type_id::create("sb", this);
    endfunction

    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        this.sb.exp_fifo.analysis_export.connect(this.agent.in_mon.ap);
        this.sb.act_fifo.analysis_export.connect(this.agent.out_mon.ap);
    endfunction

endclass : SHA3Env

`endif // SHA3ENV_SV
