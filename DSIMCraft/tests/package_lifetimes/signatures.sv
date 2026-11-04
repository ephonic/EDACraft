`timescale 1ns/1ps
package automatic types_pkg;
 typedef logic[11:0] word_t;
 function static word_t named(input word_t x);word_t n=12'h100;begin n+=x;return n;end endfunction
 function static [11:0] packed_f(input logic[11:0] x);logic[11:0] n=12'h200;begin n+=x;return n;end endfunction
 function static scalar_f(input logic x);logic n=0;begin n^=x;return n;end endfunction
 function integer step(ref integer x);integer n=1;begin x+=n;return x;end endfunction
 task static old_style;input integer x;output integer y;integer n=7;begin n+=x;y=n;end endtask
endpackage
module lane #(parameter BIAS=2)(output integer result);
 function static integer kept(input integer x);integer n=10;begin n+=x;return n;end endfunction
 function automatic integer fresh(input integer x);integer n=10;begin n+=x;return n;end endfunction
 integer a,b,c,d;
 initial begin a=kept(BIAS);b=kept(BIAS);c=fresh(BIAS);d=fresh(BIAS);result=a+b+c+d;
 #2;if(result!=40+5*BIAS)$fatal(1,"module static lifetime clone");end
endmodule
module top;
 integer one,two,a,b,c=5,d,e,f;logic[11:0] x,y,z,w;logic bit_a,bit_b;
 lane #(.BIAS(2)) l(one);lane #(.BIAS(3)) r(two);
 initial begin
 x=types_pkg::named(1);y=types_pkg::named(1);z=types_pkg::packed_f(2);w=types_pkg::packed_f(2);
 bit_a=types_pkg::scalar_f(1);bit_b=types_pkg::scalar_f(1);
 a=types_pkg::step(c);b=types_pkg::step(c);types_pkg::old_style(2,d);types_pkg::old_style(2,e);
 #3;if(x!=257||y!=258||z!=514||w!=516||bit_a!=1||bit_b!=0||a!=6||b!=7||c!=7||d!=9||e!=11||one!=50||two!=55)$fatal(1,"signature lifetime");
 $display("TRACE signatures %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",x,y,z,w,bit_a,bit_b,a,b,c,d,e,one,two);
 end
endmodule
