`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0;
    wire [31:0] d0, d1, d2, d3, d4, d5, d6, d7;
    wire halted;
    wire [31:0] retire;
    rv32i5 dut (
        .clk(clk), .rst_n(rst_n), .halted(halted), .retire(retire),
        .dbg0(d0), .dbg1(d1), .dbg2(d2), .dbg3(d3),
        .dbg4(d4), .dbg5(d5), .dbg6(d6), .dbg7(d7)
    );
    always #5 clk = ~clk;
    integer cyc;
    initial begin
        cyc = 0;
        @(posedge clk); #1; @(posedge clk); #1; rst_n = 1;
        while (!halted && cyc < 20000000) begin
            @(posedge clk); #1; cyc = cyc + 1;
        end
        repeat (4) @(posedge clk); #1;
        if (d0 === 32'd2999999 && d1 === 32'd1500000)
            $display("PERF cpu: PASS checksum=0x%08x retire=%0d cycles=%0d",
                     d0 + d1, retire, cyc);
        else
            $display("PERF cpu: FAIL d0=%0d d1=%0d", d0, d1);
        $finish;
    end
endmodule
