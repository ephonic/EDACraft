// small counter design for VCD waveform probe
`timescale 1ns/1ps
module top;
    reg clk = 0, rst_n = 0;
    reg [3:0] cnt = 0;
    always #5 clk = ~clk;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) cnt <= 4'd0; else cnt <= cnt + 4'd1;
    initial begin
        @(posedge clk); #1; rst_n = 1;
        repeat (10) @(posedge clk);
        $display("VCD_PROBE: cnt=%0d", cnt);
        $finish;
    end
endmodule
