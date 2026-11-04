// probe: $past/$rose/$stable sampled value functions
`timescale 1ns/1ps
module tb;
    reg clk = 0;
    reg [3:0] v = 0;
    reg [3:0] past_v;
    reg rose_v, stab_v;
    always #5 clk = ~clk;
    always_ff @(posedge clk) v <= v + 1;
    always_ff @(posedge clk) begin
        past_v <= $past(v);
        rose_v <= $rose(v[0]);
        stab_v <= $stable(v[1]);
    end
    initial begin
        repeat (6) @(posedge clk);
        #1;
        $display("PROBE_SAMPLED: past=%0d rose=%b stable=%b", past_v, rose_v, stab_v);
        $finish;
    end
endmodule
