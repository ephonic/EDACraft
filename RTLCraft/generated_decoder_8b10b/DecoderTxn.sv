// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : DecoderTxn.sv
// Module Name : DecoderTxn
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef DECODERTXN_SV
`define DECODERTXN_SV

import decoder_8b10b_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class DecoderTxn extends uvm_sequence_item;
    `uvm_object_utils_begin(DecoderTxn)
        `uvm_field_int(decoder_in, UVM_ALL_ON)
        `uvm_field_int(control_in, UVM_ALL_ON)
        `uvm_field_int(decoder_valid_in, UVM_ALL_ON)
        `uvm_field_int(decoder_out, UVM_ALL_ON)
        `uvm_field_int(control_out, UVM_ALL_ON)
        `uvm_field_int(decoder_valid_out, UVM_ALL_ON)
    `uvm_object_utils_end

    rand logic [9:0] decoder_in;
    rand logic control_in;
    rand logic decoder_valid_in;
    rand logic [7:0] decoder_out;
    rand logic control_out;
    rand logic decoder_valid_out;

    function new(string name = "DecoderTxn");
        super.new(name);
    endfunction

endclass : DecoderTxn

`endif // DECODERTXN_SV
