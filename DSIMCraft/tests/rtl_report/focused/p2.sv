`timescale 1ns/1ps
module p2;
    reg a = 0;
    task delayed; begin #1 a = 1; end endtask
    initial begin delayed; $display("p2 a=%0d", a); $finish; end
endmodule
