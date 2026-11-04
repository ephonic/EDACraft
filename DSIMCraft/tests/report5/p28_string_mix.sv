// probe: string literal + integer arithmetic, multi-char literal truncation
`timescale 1ns/1ps
module tb;
    reg [7:0] i = 3;
    reg [7:0] r, s;
    reg [15:0] w;
    initial begin
        #1;
        r = "1" + i;        // 0x31 + 3 = 52
        s = "AB";           // 16'h4142 -> 8b truncate = 0x42
        w = "AB";           // 16'h4142
        #1;
        if (r == 8'd52 && s == 8'h42 && w == 16'h4142)
            $display("PROBE_STRMIX: ok");
        else
            $display("PROBE_STRMIX: BAD r=%0d s=%h w=%h", r, s, w);
        $finish;
    end
endmodule
