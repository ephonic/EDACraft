`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0;
    wire [31:0] pc;
    wire [31:0] d0, d1, d2, d3, d4, d5, d6, d7;
    wire halted;
    wire [31:0] retire;

    rv32i_core dut (
        .clk(clk), .rst_n(rst_n), .dbg_pc(pc),
        .dbg0(d0), .dbg1(d1), .dbg2(d2), .dbg3(d3),
        .dbg4(d4), .dbg5(d5), .dbg6(d6), .dbg7(d7),
        .halted(halted), .retire(retire)
    );

    always #5 clk = ~clk;

`include "expected.svh"

    integer errors, cyc;
    initial begin
        errors = 0; cyc = 0;
        @(posedge clk); #1; rst_n = 1;
        while (!halted && cyc < 1000) begin
            @(posedge clk); #1; cyc = cyc + 1;
        end
        if (!halted) begin
            errors = errors + 1;
            $display("FAIL: timeout, pc=%h retire=%0d", pc, retire);
        end else begin
            if (d0 !== DBG0) begin errors = errors + 1; $display("FAIL dbg0: %h expected %h", d0, DBG0); end
            if (d1 !== DBG1) begin errors = errors + 1; $display("FAIL dbg1: %h expected %h", d1, DBG1); end
            if (d2 !== DBG2) begin errors = errors + 1; $display("FAIL dbg2: %h expected %h", d2, DBG2); end
            if (d3 !== DBG3) begin errors = errors + 1; $display("FAIL dbg3: %h expected %h", d3, DBG3); end
            if (d4 !== DBG4) begin errors = errors + 1; $display("FAIL dbg4: %h expected %h", d4, DBG4); end
            if (d5 !== DBG5) begin errors = errors + 1; $display("FAIL dbg5: %h expected %h", d5, DBG5); end
            if (d6 !== DBG6) begin errors = errors + 1; $display("FAIL dbg6: %h expected %h", d6, DBG6); end
            if (d7 !== DBG7) begin errors = errors + 1; $display("FAIL dbg7: %h expected %h", d7, DBG7); end
            $display("retired %0d instructions in %0d cycles", retire, cyc);
        end
        if (errors == 0) $display("RV32I_TEST: ALL PASS");
        else             $display("RV32I_TEST: %0d ERRORS", errors);
        $finish;
    end
endmodule
