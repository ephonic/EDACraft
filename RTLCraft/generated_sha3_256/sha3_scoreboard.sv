// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : sha3_scoreboard.sv
// Module Name : SHA3Scoreboard
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef SHA3SCOREBOARD_SV
`define SHA3SCOREBOARD_SV

import sha3_256_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"
import "DPI-C" function void dpi_sha3_256(input longint block[17], input int len, output longint hash[4]);

class SHA3Scoreboard extends uvm_component;
    `uvm_component_utils(SHA3Scoreboard)

    uvm_tlm_analysis_fifo #(SHA3Txn) exp_fifo;
    uvm_tlm_analysis_fifo #(SHA3Txn) act_fifo;
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
        SHA3Txn exp_txn;
        SHA3Txn act_txn;
        total = (0);
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

    virtual function void check(SHA3Txn exp_txn, SHA3Txn act_txn);
        int expected;
        longint block_arr [17] = '{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
        longint hash_out [4] = '{0, 0, 0, 0};
        for (int i = 0; i < 17; i = i + 1) begin
            block_arr[i] = ((exp_txn.block >> (i * 64)) & 18446744073709551615);
        end
        dpi_sha3_256(block_arr, exp_txn.msg_len, hash_out);
        expected = 0;
        for (int i = 0; i < 4; i = i + 1) begin
            expected = (expected | (hash_out[i] << (i * 64)));
        end
        if (act_txn.hash == expected) begin
            this.passes += 1;
        end else begin
            this.errors += 1;
            uvm_error("SB", $sformatf("Mismatch msg_len=%0d -> exp=%0d act=%0d", exp_txn.msg_len, expected, act_txn.hash));
        end
    endfunction

endclass : SHA3Scoreboard

`endif // SHA3SCOREBOARD_SV
