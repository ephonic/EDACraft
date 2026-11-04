// probe: force/release on reg
`timescale 1ns/1ps
module tb;
    reg clk = 0;
    reg [3:0] c = 0;
    always #5 clk = ~clk;
    always @(posedge clk) c <= c + 1;
    initial begin
        @(posedge clk); @(posedge clk); #1;
        force c = 4'd9;
        @(posedge clk); #1;
        if (c === 4'd9) $display("PROBE_FORCE: force ok");
        else            $display("PROBE_FORCE: force BAD %h", c);
        release c;
        @(posedge clk); #1;
        $display("PROBE_FORCE: after release %h", c);
        $finish;
    end
endmodule
