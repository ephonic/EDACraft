`timescale 1ns/1ps
package automatic pure_pkg;
 function integer next_value(input integer x);integer n=2;begin n+=x;return n;end endfunction
endpackage
module lane #(parameter BIAS=1)(output integer value);
 integer i;
 initial begin value=BIAS;for(i=0;i<4;i++)begin #1;value=pure_pkg::next_value(value);end end
endmodule
module top;
 integer one,two;lane #(.BIAS(1)) l(one);lane #(.BIAS(10)) r(two);
endmodule
