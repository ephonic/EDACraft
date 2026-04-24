// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : fp8_alu_directed_seq.sv
// Module Name : FP8ALUDirectedSeq
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef FP8ALUDIRECTEDSEQ_SV
`define FP8ALUDIRECTEDSEQ_SV

import fp8_alu_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class FP8ALUDirectedSeq extends uvm_sequence #(FP8ALUTxn);
    `uvm_component_utils(FP8ALUDirectedSeq)

    virtual task body();
        int count;
        int op;
        int a;
        int b;
        FP8ALUTxn txn;
        count = 0;
        for (int op_idx = 0; op_idx < 7; op_idx = op_idx + 1) begin
            op = OPS[op_idx];
            for (int a_idx = 0; a_idx < 11; a_idx = a_idx + 1) begin
                a = SPECIAL_VALS[a_idx];
                for (int b_idx = 0; b_idx < 11; b_idx = b_idx + 1) begin
                    b = SPECIAL_VALS[b_idx];
                    txn = FP8ALUTxn::type_id::create("txn");
                    `uvm_do_with(txn, {"a" == a; "b" == b; "op" == op;})
                    count += 1;
                end
            end
        end
        this.num_transactions = count;
        uvm_info("DSEQ", $sformatf("Directed sequence sent %0d transactions", count), 0);
    endtask

endclass : FP8ALUDirectedSeq

`endif // FP8ALUDIRECTEDSEQ_SV
