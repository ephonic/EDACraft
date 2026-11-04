`timescale 1ps/1ps
module top;
 class Box#(type T=int);T n;function new(T v);n=v;endfunction endclass
 Box#(logic[64:0]) a;logic[64:0] one=0;int two=0;
 initial begin a=new(7);#2;one=a.n;#2;a.n=9;one=a.n;end
 initial begin #1;two=11;#2;two=23;end
endmodule
