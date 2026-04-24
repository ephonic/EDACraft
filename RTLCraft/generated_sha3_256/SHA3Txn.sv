// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : SHA3Txn.sv
// Module Name : SHA3Txn
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef SHA3TXN_SV
`define SHA3TXN_SV

import sha3_256_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class SHA3Txn extends uvm_sequence_item;
    `uvm_object_utils_begin(SHA3Txn)
        `uvm_field_int(msg_len, UVM_ALL_ON)
        `uvm_field_int(block, UVM_ALL_ON)
        `uvm_field_int(hash, UVM_ALL_ON)
    `uvm_object_utils_end

    rand logic [7:0] msg_len;
    rand logic [1087:0] block;
    rand logic [255:0] hash;

    function new(string name = "SHA3Txn");
        super.new(name);
    endfunction

endclass : SHA3Txn

`endif // SHA3TXN_SV
