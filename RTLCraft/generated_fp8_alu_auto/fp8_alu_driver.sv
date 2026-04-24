// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : fp8_alu_driver.sv
// Module Name : FP8ALUDriver
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef FP8ALUDRIVER_SV
`define FP8ALUDRIVER_SV

import fp8_alu_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class FP8ALUDriver extends uvm_driver #(FP8ALUTxn);
    `uvm_component_utils(FP8ALUDriver)

    virtual task run_phase(uvm_phase phase);
        FP8ALUTxn req;
        forever begin
            this.seq_item_port.get_next_item(req);
            while ((!this.vif.cb.i_ready)) begin
                @vif.cb;
            end
            this.vif.cb.i_valid <= 1;
            this.vif.cb.a <= req.a;
            this.vif.cb.b <= req.b;
            this.vif.cb.op <= req.op;
            @vif.cb;
            this.vif.cb.i_valid <= 0;
            this.seq_item_port.item_done();
        end
    endtask

endclass : FP8ALUDriver

`endif // FP8ALUDRIVER_SV
