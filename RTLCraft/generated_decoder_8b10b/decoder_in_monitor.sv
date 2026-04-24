// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : decoder_in_monitor.sv
// Module Name : DecoderInMonitor
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef DECODERINMONITOR_SV
`define DECODERINMONITOR_SV

import decoder_8b10b_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class DecoderInMonitor extends uvm_monitor;
    `uvm_component_utils(DecoderInMonitor)

    uvm_analysis_port #(DecoderTxn) ap;

    virtual task run_phase(uvm_phase phase);
        DecoderTxn txn;
        forever begin
            @vif.cb;
            if (this.vif.cb.decoder_valid_in) begin
                txn = DecoderTxn::type_id::create("txn");
                txn.decoder_in = this.vif.cb.decoder_in;
                txn.control_in = this.vif.cb.control_in;
                txn.decoder_valid_in = 1;
                this.ap.write(txn);
            end
        end
    endtask

endclass : DecoderInMonitor

`endif // DECODERINMONITOR_SV
