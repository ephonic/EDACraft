`timescale 1ns/1ps
module automatic typed_lane #(parameter BIAS=2)(output integer result);
 typedef logic[11:0] word_t;
 function word_t named(input word_t x);word_t n=12'h100;n+=x;return n;endfunction
 function [11:0] packed_f(input logic[11:0] x);logic[11:0] n=12'h200;n+=x;return n;endfunction
 function static scalar_f(input logic x);logic n=0;n^=x;return n;endfunction
 function integer step(ref integer x);integer n=1;x+=n;return x;endfunction
 function integer count();static integer n=10;n++;return n;endfunction
 task old_style;input integer x;output integer y;integer n=7;begin n+=x;y=n;end endtask
 integer a,b,c=5,d,e,k,l;logic[11:0] x,y,z,w;logic bit_a,bit_b;
 initial begin
 x=named(BIAS);y=named(BIAS);z=packed_f(BIAS);w=packed_f(BIAS);
 bit_a=scalar_f(1);bit_b=scalar_f(1);a=step(c);b=step(c);old_style(BIAS,d);old_style(BIAS,e);k=count();l=count();
 result=x+y+z+w+d+e;
 #1;if(x!=256+BIAS||y!=256+BIAS||z!=512+BIAS||w!=512+BIAS||bit_a!=1||bit_b!=0||a!=6||b!=7||c!=7||d!=7+BIAS||e!=7+BIAS||k!=11||l!=12)$fatal(1,"typed unit lifetime");
 end
endmodule
module top;
 integer one,two;typed_lane #(.BIAS(2)) a(one);typed_lane #(.BIAS(3)) b(two);
 initial begin #2;if(one!=1562||two!=1568)$fatal(1,"typed clone identity");$display("TRACE signatures %0d %0d",one,two);end
endmodule
