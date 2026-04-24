// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : decoder_driver.sv
// Module Name : DecoderDriver
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef DECODERDRIVER_SV
`define DECODERDRIVER_SV

import decoder_8b10b_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class DecoderDriver extends uvm_driver #(DecoderTxn);
    `uvm_component_utils(DecoderDriver)

    virtual task run_phase(uvm_phase phase);
        DecoderTxn req;
        forever begin
            this.seq_item_port.get_next_item(req);
            this.vif.cb.control_in <= req.control_in;
            this.vif.cb.decoder_in <= req.decoder_in;
            this.vif.cb.decoder_valid_in <= req.decoder_valid_in;
            @vif.cb;
            this.seq_item_port.item_done();
        end
    endtask

endclass : DecoderDriver

`endif // DECODERDRIVER_SV
