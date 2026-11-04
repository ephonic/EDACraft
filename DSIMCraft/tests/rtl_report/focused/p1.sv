`timescale 1ns/1ps
module p1;
    reg a = 0;
    task incr; begin a = a + 1; end endtask
    initial begin incr; incr; $display("p1 a=%0d", a); $finish; end
endmodule
