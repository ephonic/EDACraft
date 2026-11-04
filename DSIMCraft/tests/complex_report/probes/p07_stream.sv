// probe: streaming concatenation {<<{...}}
`timescale 1ns/1ps
module tb;
    reg [7:0] x = 8'hB4;   // 1011_0100
    reg [7:0] r;
    initial begin
        r = {<<{x}};       // expect 8'h2D (0010_1101)
        if (r == 8'h2D) $display("PROBE_STREAM: ok 2D");
        else            $display("PROBE_STREAM: BAD %h", r);
        $finish;
    end
endmodule
