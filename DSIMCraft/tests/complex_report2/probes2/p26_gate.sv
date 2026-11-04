// gate-level probe: inverter + and/or tree
`timescale 1ns/1ps
module g_inv (input a, output y);
    assign #1 y = ~a;
endmodule
module g_and (input a, input b, output y);
    assign #1 y = a & b;
endmodule
module g_or (input a, input b, output y);
    assign #1 y = a | b;
endmodule

module top (input wire a, input wire b, input wire c, output wire y);
    wire n1, a1, a2;
    g_inv  u1 (.a(a), .y(n1));
    g_and  u2 (.a(n1), .b(b), .y(a1));
    g_and  u3 (.a(a), .b(c), .y(a2));
    g_or   u4 (.a(a1), .b(a2), .y(y));
endmodule

module tb;
    reg a = 0, b = 0, c = 0;
    wire y;
    top dut (.a(a), .b(b), .c(c), .y(y));
    initial begin
        #3 a = 1; b = 1; c = 0;
        #5 c = 1;
        #5 b = 0;
        #5 $display("GATE_PROBE: y=%b", y);   // zero-delay sim: a=1,b=0,c=1 -> (0&0)|(1&1)=1
        $finish;
    end
endmodule
