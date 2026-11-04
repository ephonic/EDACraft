`timescale 1ps/1ps
module top;
 class Box#(type T=int, U=T);T n;function new(T v);n=v;endfunction endclass
 function logic[64:0] read_box(int bias,Box#(logic[64:0]) obj);return bias+obj.n;endfunction
 Box#(logic[64:0]) a;logic[64:0] one=0;int two=0;
 initial begin a=new(7);#2;one=read_box(0,a);#2;a.n=9;one=read_box(0,a);end
 initial begin #1;two=11;#2;two=23;end
endmodule
