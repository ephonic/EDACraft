// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : decoder_scoreboard.sv
// Module Name : DecoderScoreboard
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef DECODERSCOREBOARD_SV
`define DECODERSCOREBOARD_SV

import decoder_8b10b_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"
import "DPI-C" function void dpi_decoder_8b10b_ref(input int decoder_in, input int control_in, output int decoder_out, output int control_out);

class DecoderScoreboard extends uvm_component;
    `uvm_component_utils(DecoderScoreboard)

    uvm_tlm_analysis_fifo #(DecoderTxn) exp_fifo;
    uvm_tlm_analysis_fifo #(DecoderTxn) act_fifo;
    int errors;
    int passes;

    function new(string name, uvm_component parent);
        super.new(name, parent);
        this.exp_fifo = new("exp_fifo", this);
        this.act_fifo = new("act_fifo", this);
        this.errors = 0;
        this.passes = 0;
    endfunction

    virtual task run_phase(uvm_phase phase);
        int total;
        int checked;
        DecoderTxn exp_txn;
        DecoderTxn act_txn;
        if (!uvm_config_db#(int)::get(this, "", "total_txn_count", total))
            total = 0;
        phase.raise_objection(this);
        checked = 0;
        while (checked < total) begin
            this.exp_fifo.get(exp_txn);
            this.act_fifo.get(act_txn);
            this.check(exp_txn, act_txn);
            checked += 1;
        end
        phase.drop_objection(this);
    endtask

    virtual function void report_phase(uvm_phase phase);
        $display($sformatf("[SCOREBOARD] passes=%0d errors=%0d", this.passes, this.errors));
    endfunction

    virtual function void check(DecoderTxn exp_txn, DecoderTxn act_txn);
        int expected_out;
        int expected_ctrl;
        logic out_arr [1] = '{0};
        logic ctrl_arr [1] = '{0};
        dpi_decoder_8b10b_ref(exp_txn.decoder_in, exp_txn.control_in, out_arr, ctrl_arr);
        expected_out = out_arr[0];
        expected_ctrl = ctrl_arr[0];
        if ((act_txn.decoder_out == expected_out) && (act_txn.control_out == expected_ctrl)) begin
            this.passes += 1;
        end else begin
            this.errors += 1;
            uvm_error("SB", $sformatf("Mismatch in=0b%0d ctrl=%0d exp_out=0b%0d exp_ctrl=%0d act_out=0b%0d act_ctrl=%0d", exp_txn.decoder_in, exp_txn.control_in, expected_out, expected_ctrl, act_txn.decoder_out, act_txn.control_out));
        end
    endfunction

endclass : DecoderScoreboard

`endif // DECODERSCOREBOARD_SV
