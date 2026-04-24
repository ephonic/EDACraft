// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : fp8_alu_agent.sv
// Module Name : FP8ALUAgent
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef FP8ALUAGENT_SV
`define FP8ALUAGENT_SV

import fp8_alu_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class FP8ALUAgent extends uvm_agent;
    `uvm_component_utils(FP8ALUAgent)

    uvm_sequencer #(uvm_sequence_item) sqr;
    FP8ALUDriver drv;
    FP8ALUInMonitor in_mon;
    FP8ALUOutMonitor out_mon;

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        sqr = UVMSequencer::type_id::create("sqr", this);
        drv = FP8ALUDriver::type_id::create("drv", this);
        in_mon = FP8ALUInMonitor::type_id::create("in_mon", this);
        out_mon = FP8ALUOutMonitor::type_id::create("out_mon", this);
    endfunction

    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        this.drv.seq_item_port.connect(this.sqr.seq_item_export);
    endfunction

endclass : FP8ALUAgent

`endif // FP8ALUAGENT_SV
