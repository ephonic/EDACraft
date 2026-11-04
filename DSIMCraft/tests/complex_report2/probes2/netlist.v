// gate netlist only (for --gate-netlist parsing)
module top (a, b, c, y);
    input a, b, c;
    output y;
    wire n1, a1, a2;
    g_inv u1 (.a(a), .y(n1));
    g_and u2 (.a(n1), .b(b), .y(a1));
    g_and u3 (.a(a), .b(c), .y(a2));
    g_or  u4 (.a(a1), .b(a2), .y(y));
endmodule
