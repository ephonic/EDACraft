// probe: size casts N'(expr) and type casts
`timescale 1ns/1ps
module tb;
    integer i = 300;
    reg [7:0] b;
    reg [15:0] w;
    initial begin
        b = 8'(i);          // truncate to 300 & 0xFF = 44
        w = 16'(i);         // 300
        if (b == 8'd44 && w == 16'd300)
            $display("PROBE_SIZECAST: ok");
        else
            $display("PROBE_SIZECAST: BAD b=%0d w=%0d", b, w);
        $finish;
    end
endmodule
