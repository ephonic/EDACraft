`timescale 1ns/1ps
module t06;
    integer a, b;
    initial begin
        a = $urandom;
        b = $urandom_range(0, 49);
        if (b >= 0 && b <= 49) $display("T06_URANDOM PASS a=%0d b=%0d", a, b);
        else $display("T06_URANDOM FAIL b=%0d", b);
        $finish;
    end
endmodule
