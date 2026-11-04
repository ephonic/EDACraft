`timescale 1ns/1ps
package pkg3;
    typedef enum logic [1:0] { A, B, C } st_e;
    function automatic integer double(integer x); return x*2; endfunction
endpackage
module t03;
    import pkg3::*;
    integer v;
    initial begin
        v = double(21);
        if (v == 42 && B == 2'd1) $display("T03_PACKAGE PASS"); else $display("T03_PACKAGE FAIL v=%0d", v);
        $finish;
    end
endmodule
