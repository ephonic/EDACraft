// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : fp8_alu_test.sv
// Module Name : FP8ALUTest
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef FP8ALUTEST_SV
`define FP8ALUTEST_SV

import fp8_alu_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class FP8ALUTest extends uvm_test;
    `uvm_component_utils(FP8ALUTest)

    FP8ALUEnv env;

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        env = FP8ALUEnv::type_id::create("env", this);
        uvm_config_db#(int)::set(this, "", "total_txn_count", 0);
    endfunction

    virtual task run_phase(uvm_phase phase);
        int total;
        FP8ALUDirectedSeq dseq;
        FP8ALURandomSeq rseq;
        phase.raise_objection(this);
        total = 1047;
        uvm_config_db#(int)::set(this, "", "total_txn_count", total);
        dseq = FP8ALUDirectedSeq::type_id::create("dseq", this);
        rseq = FP8ALURandomSeq::type_id::create("rseq", this);
        dseq.start(this.env.agent.sqr);
        rseq.start(this.env.agent.sqr);
        repeat (15) @vif.cb;
        phase.drop_objection(this);
    endtask

endclass : FP8ALUTest

`endif // FP8ALUTEST_SV
