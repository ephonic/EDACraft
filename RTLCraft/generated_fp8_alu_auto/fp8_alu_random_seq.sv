// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : fp8_alu_random_seq.sv
// Module Name : FP8ALURandomSeq
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef FP8ALURANDOMSEQ_SV
`define FP8ALURANDOMSEQ_SV

import fp8_alu_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class FP8ALURandomSeq extends uvm_sequence #(FP8ALUTxn);
    `uvm_component_utils(FP8ALURandomSeq)

    virtual task body();
        FP8ALUTxn txn;
        for (int i = 0; i < this.num_transactions; i = i + 1) begin
            txn = FP8ALUTxn::type_id::create("txn");
            `uvm_do_with(txn, {"a" inside {[0:255]}; "b" inside {[0:255]}; "op" inside {[0:6]};})
        end
        uvm_info("RSEQ", $sformatf("Random sequence sent %0d transactions", this.num_transactions), 0);
    endtask

endclass : FP8ALURandomSeq

`endif // FP8ALURANDOMSEQ_SV
