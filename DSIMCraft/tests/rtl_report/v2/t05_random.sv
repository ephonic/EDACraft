`timescale 1ns/1ps
module t05;
    integer r1, r2; integer i; integer seed = 7;
    reg [31:0] seen;
    initial begin
        r1 = $random; r2 = $random(seed);
        seen = 0;
        for (i = 0; i < 32; i = i + 1) seen[i] = 1'b1;
        if (r1 !== r1) $display("T05_RANDOM FAIL X");
        else $display("T05_RANDOM PASS r1=%0d r2=%0d", r1, r2);
        $finish;
    end
endmodule
