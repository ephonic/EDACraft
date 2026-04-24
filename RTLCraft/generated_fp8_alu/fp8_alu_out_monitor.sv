// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : fp8_alu_out_monitor.sv
// Module Name : FP8ALUOutMonitor
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef FP8ALUOUTMONITOR_SV
`define FP8ALUOUTMONITOR_SV

import fp8_alu_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class FP8ALUOutMonitor extends uvm_monitor;
    `uvm_component_utils(FP8ALUOutMonitor)

    virtual task run_phase(uvm_phase phase);
        FP8ALUTxn txn;
        forever begin
            @vif.cb;
            if ((this.vif.cb.o_valid) && (this.vif.cb.o_ready)) begin
                txn = FP8ALUTxn::type_id::create("txn");
                txn.result = this.vif.cb.result;
                txn.flags = this.vif.cb.flags;
                this.ap.write(txn);
            end
        end
    endtask

endclass : FP8ALUOutMonitor

`endif // FP8ALUOUTMONITOR_SV
