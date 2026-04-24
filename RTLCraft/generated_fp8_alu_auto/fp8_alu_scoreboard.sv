// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : fp8_alu_scoreboard.sv
// Module Name : FP8ALUScoreboard
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef FP8ALUSCOREBOARD_SV
`define FP8ALUSCOREBOARD_SV

import fp8_alu_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class FP8ALUScoreboard extends uvm_component;
    `uvm_component_utils(FP8ALUScoreboard)

    int total_txn_count;
    uvm_tlm_analysis_fifo #(FP8ALUTxn) exp_fifo;
    uvm_tlm_analysis_fifo #(FP8ALUTxn) act_fifo;
    int errors;
    int passes;
    Coverage cov_op;
    Coverage cov_a_class;
    Coverage cov_b_class;
    Coverage cov_cross;
    Coverage cov_flags;

    function new(string name, uvm_component parent);
        super.new(name, parent);
        this.total_txn_count = 1047;
        this.exp_fifo = new("exp_fifo", this);
        this.act_fifo = new("act_fifo", this);
        this.errors = 0;
        this.passes = 0;
        string classes [5] = '{"zero", "subnormal", "normal", "inf", "nan"};
    endfunction

    virtual task run_phase(uvm_phase phase);
        int checked;
        FP8ALUTxn exp_txn;
        FP8ALUTxn act_txn;
        phase.raise_objection(this);
        checked = 0;
        while (checked < this.total_txn_count) begin
            this.exp_fifo.get(exp_txn);
            this.act_fifo.get(act_txn);
            // omitted: this._check(...)
            checked += 1;
        end
        phase.drop_objection(this);
    endtask

    virtual function void report_phase(uvm_phase phase);
        $display($sformatf("[SCOREBOARD] passes=%0d errors=%0d", this.passes, this.errors));
    endfunction

endclass : FP8ALUScoreboard

`endif // FP8ALUSCOREBOARD_SV
