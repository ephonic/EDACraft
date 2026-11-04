`timescale 1ps/1ps
module top;
 class Box;int n;function new(int value);n=value;endfunction endclass
 Box q[$],b;int one=0,two=0;
 initial begin b=new(7);q.push_back(b);#2;one=q.pop_front().n;#2;b.n=9;one=b.n;end
 initial begin #1;two=11;#2;two=23;end
endmodule
