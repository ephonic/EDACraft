// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : decoder_test.sv
// Module Name : DecoderTest
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

`ifndef DECODERTEST_SV
`define DECODERTEST_SV

import decoder_8b10b_pkg::*;
import uvm_pkg::*;
`include "uvm_macros.svh"

class DecoderTest extends uvm_test;
    `uvm_component_utils(DecoderTest)

    DecoderEnv env;

    function new(string name, uvm_component parent);
        super.new(name);
        this.dut = dut;
    endfunction

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        env = DecoderEnv::type_id::create("env", this);
        uvm_config_db#(int)::set(this, "", "total_txn_count", len(DecoderDirectedSeq._get_txns()));
    endfunction

    virtual task run_phase(uvm_phase phase);
        DecoderDirectedSeq dseq;
        phase.raise_objection(this);
        dseq = DecoderDirectedSeq::type_id::create("dseq", this);
        dseq.start(this.env.agent.sqr);
        repeat (5) @vif.cb;
        phase.drop_objection(this);
    endtask

endclass : DecoderTest

`endif // DECODERTEST_SV
