`timescale 1ns/1ps
package types_pkg;typedef logic [7:0] byte_t;parameter STEP=2;endpackage
module automatic lane import types_pkg::*; #(parameter BIAS=1)(output integer value);
 function byte_t next_value(input byte_t x);byte_t n=STEP;n+=x;return n;endfunction
 task advance(output integer x);integer n=BIAS;begin #1;n+=next_value(n);x=n;end endtask
 initial begin advance(value);#1;advance(value);end
endmodule
module top;
 integer one,two;
 for(genvar i=0;i<2;i++)begin: lanes
  if(i==0)begin:a lane #(.BIAS(1)) l(one);end
  else begin:b lane #(.BIAS(10)) l(two);end
 end
endmodule
