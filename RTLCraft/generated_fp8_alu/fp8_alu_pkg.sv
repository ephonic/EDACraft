// ----------------------------------------
// © Copyright CUBLAZER All Right Reserved.
//
// Abstract : Auto-generated UVM/SV file
// File Name : fp8_alu_pkg.sv
// Module Name : fp8_alu_pkg
// Revision History:
//      ver1.0  rtlgen Date
//             Initial generation
// ----------------------------------------

package fp8_alu_pkg;
    import uvm_pkg::*;
    `include "uvm_macros.svh"

    `include "FP8ALUTxn.sv"
    `include "fp8_alu_agent.sv"
    `include "fp8_alu_directed_seq.sv"
    `include "fp8_alu_driver.sv"
    `include "fp8_alu_env.sv"
    `include "fp8_alu_in_monitor.sv"
    `include "fp8_alu_out_monitor.sv"
    `include "fp8_alu_random_seq.sv"
    `include "fp8_alu_scoreboard.sv"
    `include "fp8_alu_test.sv"
endpackage : fp8_alu_pkg
