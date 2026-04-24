// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : sha3_test.sv
// Module Name : SHA3Test
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef SHA3TEST_SV
`define SHA3TEST_SV

import sha3_256_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class SHA3Test extends uvm_test;
    `uvm_component_utils(SHA3Test)

    SHA3Env env;

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        env = SHA3Env::type_id::create("env", this);
        uvm_config_db#(int)::set(this, "", "total_txn_count", 0);
    endfunction

    virtual task run_phase(uvm_phase phase);
        SHA3DirectedSeq dseq;
        phase.raise_objection(this);
        dseq = SHA3DirectedSeq::type_id::create("dseq", this);
        uvm_config_db#(int)::set(this, "", "total_txn_count", dseq.num_transactions);
        dseq.start(this.env.agent.sqr);
        repeat (30) @vif.cb;
        phase.drop_objection(this);
    endtask

endclass : SHA3Test

`endif // SHA3TEST_SV
