// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : decoder_out_monitor.sv
// Module Name : DecoderOutMonitor
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef DECODEROUTMONITOR_SV
`define DECODEROUTMONITOR_SV

import decoder_8b10b_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class DecoderOutMonitor extends uvm_monitor;
    `uvm_component_utils(DecoderOutMonitor)

    uvm_analysis_port #(DecoderTxn) ap;

    virtual task run_phase(uvm_phase phase);
        DecoderTxn txn;
        forever begin
            @vif.cb;
            if (this.vif.cb.decoder_valid_out) begin
                txn = DecoderTxn::type_id::create("txn");
                txn.decoder_out = this.vif.cb.decoder_out;
                txn.control_out = this.vif.cb.control_out;
                txn.decoder_valid_out = 1;
                this.ap.write(txn);
            end
        end
    endtask

endclass : DecoderOutMonitor

`endif // DECODEROUTMONITOR_SV
