// tb for the gate netlist
`timescale 1ns/1ps
module tb;
    reg a = 0, b = 0, c = 0;
    wire y;
    top dut (.a(a), .b(b), .c(c), .y(y));
    initial begin
        #3 a = 1; b = 1; c = 0;
        #5 c = 1;
        #5 b = 0;
        #10 $display("GATE_PROBE: y=%b", y);
        $finish;
    end
endmodule
