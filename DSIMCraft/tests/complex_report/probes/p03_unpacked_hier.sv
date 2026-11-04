// probe: hierarchical reference to unpacked array element
`timescale 1ns/1ps
module dut (input wire clk);
    reg [7:0] mem [0:3];
    always @(posedge clk) begin
        mem[0] <= 8'h11; mem[1] <= 8'h22;
    end
endmodule

module tb;
    reg clk = 0;
    always #5 clk = ~clk;
    dut u (clk);
    initial begin
        @(posedge clk); @(posedge clk); #1;
        if (u.mem[0] === 8'h11) $display("PROBE_UNPACKED_HIER: ok");
        else                    $display("PROBE_UNPACKED_HIER: BAD %h", u.mem[0]);
        $finish;
    end
endmodule
