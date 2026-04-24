// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : decoder_env.sv
// Module Name : DecoderEnv
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef DECODERENV_SV
`define DECODERENV_SV

import decoder_8b10b_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class DecoderEnv extends uvm_env;
    `uvm_component_utils(DecoderEnv)

    DecoderAgent agent;
    DecoderScoreboard sb;

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        agent = DecoderAgent::type_id::create("agent", this);
        sb = DecoderScoreboard::type_id::create("sb", this);
    endfunction

    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        this.sb.exp_fifo.analysis_export.connect(this.agent.in_mon.ap);
        this.sb.act_fifo.analysis_export.connect(this.agent.out_mon.ap);
    endfunction

endclass : DecoderEnv

`endif // DECODERENV_SV
