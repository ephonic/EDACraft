// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : FP8ALUTxn.sv
// Module Name : FP8ALUTxn
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef FP8ALUTXN_SV
`define FP8ALUTXN_SV

import fp8_alu_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class FP8ALUTxn extends uvm_sequence_item;
    `uvm_object_utils_begin(FP8ALUTxn)
        `uvm_field_int(a, UVM_ALL_ON)
        `uvm_field_int(b, UVM_ALL_ON)
        `uvm_field_int(op, UVM_ALL_ON)
        `uvm_field_int(result, UVM_ALL_ON)
        `uvm_field_int(flags, UVM_ALL_ON)
    `uvm_object_utils_end

    rand logic [7:0] a;
    rand logic [7:0] b;
    rand logic [2:0] op;
    rand logic [7:0] result;
    rand logic [3:0] flags;

    function new(string name = "FP8ALUTxn");
        super.new(name);
    endfunction

endclass : FP8ALUTxn

`endif // FP8ALUTXN_SV
