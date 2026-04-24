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
    uvm_tlm_analysis_fifo #(uvm_sequence_item) exp_fifo;
    uvm_tlm_analysis_fifo #(uvm_sequence_item) act_fifo;
    int errors;
    int passes;

    function new(string name, uvm_component parent);
        int classes;
        super.new(name, parent);
        this.total_txn_count = 1047;
        this.exp_fifo = UVMAnalysisFIFO("exp_fifo");
        this.act_fifo = UVMAnalysisFIFO("act_fifo");
        this.errors = 0;
        this.passes = 0;
        this.cov_op.define_bins(list(range(7)));
        this.cov_a_class.define_bins();
        this.cov_b_class.define_bins();
        this.cov_cross.define_bins();
        this.cov_flags.define_bins(list(range(16)));
    endfunction

    virtual task run_phase(uvm_phase phase);
        int checked;
        uvm_sequence_item exp_txn;
        uvm_sequence_item act_txn;
        phase.raise_objection(this);
        checked = 0;
        while (checked < this.total_txn_count) begin
            this.exp_fifo.get(exp_txn);
            this.act_fifo.get(act_txn);
            this._check(exp_txn, act_txn);
            checked += 1;
        end
        phase.drop_objection(this);
    endtask

    virtual function void report_phase(uvm_phase phase);
        $display($sformatf("[SCOREBOARD] passes=%0d errors=%0d", this.passes, this.errors));
        this.cov_op.report();
        this.cov_a_class.report();
        this.cov_b_class.report();
        this.cov_cross.report();
        this.cov_flags.report();
    endfunction

endclass : FP8ALUScoreboard

`endif // FP8ALUSCOREBOARD_SV
