// probe: always_latch inference
`timescale 1ns/1ps
module tb;
    reg clk = 0, en = 0;
    reg [3:0] d = 0, q;
    always #5 clk = ~clk;
    always_latch if (en) q = d;
    initial begin
        en = 1; d = 4'hA; #7;
        if (q === 4'hA) begin
            en = 0; d = 4'h5; #7;
            if (q === 4'hA) $display("PROBE_LATCH: ok held");
            else            $display("PROBE_LATCH: BAD leak %h", q);
        end else
            $display("PROBE_LATCH: BAD no latch %h", q);
        $finish;
    end
endmodule
