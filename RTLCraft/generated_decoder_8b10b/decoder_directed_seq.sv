// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : decoder_directed_seq.sv
// Module Name : DecoderDirectedSeq
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef DECODERDIRECTEDSEQ_SV
`define DECODERDIRECTEDSEQ_SV

import decoder_8b10b_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class DecoderDirectedSeq extends uvm_sequence #(DecoderTxn);
    `uvm_component_utils(DecoderDirectedSeq)

    len num_transactions;

    virtual task body();
        DecoderTxn txn;
        // Unsupported for-loop
        this.num_transactions = len(this._get_txns());
        uvm_info("DSEQ", $sformatf("Directed sequence sent %0d transactions", this.num_transactions), 0);
    endtask

endclass : DecoderDirectedSeq

`endif // DECODERDIRECTEDSEQ_SV
