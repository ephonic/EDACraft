// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : sha3_out_monitor.sv
// Module Name : SHA3OutMonitor
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef SHA3OUTMONITOR_SV
`define SHA3OUTMONITOR_SV

import sha3_256_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class SHA3OutMonitor extends uvm_monitor;
    `uvm_component_utils(SHA3OutMonitor)

    uvm_analysis_port #(SHA3Txn) ap;

    virtual task run_phase(uvm_phase phase);
        SHA3Txn txn;
        forever begin
            @vif.cb;
            if ((this.vif.cb.o_valid) && (this.vif.cb.o_ready)) begin
                txn = SHA3Txn::type_id::create("txn");
                txn.hash = this.vif.cb.hash;
                this.ap.write(txn);
            end
        end
    endtask

endclass : SHA3OutMonitor

`endif // SHA3OUTMONITOR_SV
