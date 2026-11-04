`timescale 1ns/1ps
package arithmetic;
 function automatic integer next_value(integer n);return n+1;endfunction
endpackage
module lane #(parameter integer SEED=0)(output logic[15:0] q);
 import arithmetic::*;
 initial begin q=SEED;repeat(3)begin #1;q=next_value(q);end end
endmodule
module top;
 wire[15:0] one,two;
 lane #(.SEED('h8000)) a(one);lane #(.SEED('h8000)) b(two);
endmodule
