// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : fp8_alu_env.sv
// Module Name : FP8ALUEnv
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef FP8ALUENV_SV
`define FP8ALUENV_SV

import fp8_alu_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class FP8ALUEnv extends uvm_env;
    `uvm_component_utils(FP8ALUEnv)

    FP8ALUAgent agent;
    FP8ALUScoreboard sb;

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        agent = FP8ALUAgent::type_id::create("agent", this);
        sb = FP8ALUScoreboard::type_id::create("sb", this);
    endfunction

    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        this.sb.exp_fifo.analysis_export.connect(this.agent.in_mon.ap);;
        this.sb.act_fifo.analysis_export.connect(this.agent.out_mon.ap);;
    endfunction

endclass : FP8ALUEnv

`endif // FP8ALUENV_SV
