`timescale 1ns/1ps
module p3;
    reg clk = 0;
    always #5 clk = ~clk;
    task tick; begin @(posedge clk); end endtask
    reg a = 0;
    initial begin tick; a = 1; $display("p3 a=%0d clk=%b", a, clk); $finish; end
endmodule
