// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : sha3_directed_seq.sv
// Module Name : SHA3DirectedSeq
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef SHA3DIRECTEDSEQ_SV
`define SHA3DIRECTEDSEQ_SV

import sha3_256_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class SHA3DirectedSeq extends uvm_sequence #(SHA3Txn);
    `uvm_component_utils(SHA3DirectedSeq)

    len num_transactions;

    virtual task body();
        SHA3Txn txn;
        int block;
        logic vectors [4] = '{b'', b'abc', b'hello world', bytes(range(MAX_MSG_LEN))};
        for (int msg_idx = 0; msg_idx < $size(vectors); msg_idx = msg_idx + 1) begin
            automatic var msg = vectors[msg_idx];
            txn = SHA3Txn::type_id::create("txn");
            block = int.from_bytes(msg, "little");
            `uvm_do_with(txn, {"msg_len" == len(msg); "block" == block;})
        end
        this.num_transactions = len(vectors);
        uvm_info("DSEQ", $sformatf("Directed sequence sent %0d transactions", this.num_transactions), 0);
    endtask

endclass : SHA3DirectedSeq

`endif // SHA3DIRECTEDSEQ_SV
