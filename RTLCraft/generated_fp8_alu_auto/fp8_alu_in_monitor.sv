// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : fp8_alu_in_monitor.sv
// Module Name : FP8ALUInMonitor
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef FP8ALUINMONITOR_SV
`define FP8ALUINMONITOR_SV

import fp8_alu_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class FP8ALUInMonitor extends uvm_monitor;
    `uvm_component_utils(FP8ALUInMonitor)

    uvm_analysis_port #(FP8ALUTxn) ap;

    virtual task run_phase(uvm_phase phase);
        FP8ALUTxn txn;
        forever begin
            @vif.cb;
            if ((this.vif.cb.i_valid) && (this.vif.cb.i_ready)) begin
                txn = FP8ALUTxn::type_id::create("txn");
                txn.a = this.vif.cb.a;
                txn.b = this.vif.cb.b;
                txn.op = this.vif.cb.op;
                this.ap.write(txn);
            end
        end
    endtask

endclass : FP8ALUInMonitor

`endif // FP8ALUINMONITOR_SV
