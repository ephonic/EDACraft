// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : sha3_in_monitor.sv
// Module Name : SHA3InMonitor
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef SHA3INMONITOR_SV
`define SHA3INMONITOR_SV

import sha3_256_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class SHA3InMonitor extends uvm_monitor;
    `uvm_component_utils(SHA3InMonitor)

    uvm_analysis_port #(SHA3Txn) ap;

    virtual task run_phase(uvm_phase phase);
        SHA3Txn txn;
        forever begin
            @vif.cb;
            if ((this.vif.cb.i_valid) && (this.vif.cb.i_ready)) begin
                txn = SHA3Txn::type_id::create("txn");
                txn.msg_len = this.vif.cb.block_len;
                txn.block = this.vif.cb.block;
                this.ap.write(txn);
            end
        end
    endtask

endclass : SHA3InMonitor

`endif // SHA3INMONITOR_SV
