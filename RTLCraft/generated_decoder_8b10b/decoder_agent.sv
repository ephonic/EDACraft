// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : decoder_agent.sv
// Module Name : DecoderAgent
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef DECODERAGENT_SV
`define DECODERAGENT_SV

import decoder_8b10b_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class DecoderAgent extends uvm_agent;
    `uvm_component_utils(DecoderAgent)

    uvm_sequencer #(DecoderTxn) sqr;
    DecoderDriver drv;
    DecoderInMonitor in_mon;
    DecoderOutMonitor out_mon;

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        sqr = UVMSequencer::type_id::create("sqr", this);
        drv = DecoderDriver::type_id::create("drv", this);
        in_mon = DecoderInMonitor::type_id::create("in_mon", this);
        out_mon = DecoderOutMonitor::type_id::create("out_mon", this);
    endfunction

    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        this.drv.seq_item_port.connect(this.sqr.seq_item_export);
    endfunction

endclass : DecoderAgent

`endif // DECODERAGENT_SV
