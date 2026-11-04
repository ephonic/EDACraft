// probe: multiple always #<delay> processes
`timescale 1ns/1ps
module tb;
    reg clk = 0;
    always #5 clk = ~clk;
    always #(17) if ($time > 100000 && $time < 150000)
        $display("second always fired t=%0t", $time);
    initial begin
        #200000;
        $display("PROBE_MULTI_ALWAYS: done");
        $finish;
    end
endmodule
