// specify metadata for SDF binding
module g_inv (a, y);
    input a; output y;
    specify
        (a => y) = (1, 1);
    endspecify
    assign y = ~a;
endmodule
module g_and (a, b, y);
    input a, b; output y;
    specify
        (a => y) = (1, 1);
        (b => y) = (1, 1);
    endspecify
    assign y = a & b;
endmodule
module g_or (a, b, y);
    input a, b; output y;
    specify
        (a => y) = (1, 1);
        (b => y) = (1, 1);
    endspecify
    assign y = a | b;
endmodule
