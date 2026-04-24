// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : sha3_agent.sv
// Module Name : SHA3Agent
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef SHA3AGENT_SV
`define SHA3AGENT_SV

import sha3_256_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class SHA3Agent extends uvm_agent;
    `uvm_component_utils(SHA3Agent)

    uvm_sequencer #(SHA3Txn) sqr;
    SHA3Driver drv;
    SHA3InMonitor in_mon;
    SHA3OutMonitor out_mon;

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        sqr = UVMSequencer::type_id::create("sqr", this);
        drv = SHA3Driver::type_id::create("drv", this);
        in_mon = SHA3InMonitor::type_id::create("in_mon", this);
        out_mon = SHA3OutMonitor::type_id::create("out_mon", this);
    endfunction

    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        this.drv.seq_item_port.connect(this.sqr.seq_item_export);
    endfunction

endclass : SHA3Agent

`endif // SHA3AGENT_SV
