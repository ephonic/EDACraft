`timescale 1ns/1ps
module worker(output logic[31:0] q=0);
 integer n=3,calls=0;integer source[]=new[n];
 function automatic integer prepare();calls++;source[0]=17;return n+1;endfunction
 integer copy[]=new[prepare()](source),snapshot[]=copy;
 initial begin
  n=8;source[0]=99;
  #2;q=copy.size()+copy[0]+snapshot[0]+calls;
  #1;copy[0]=31;q=copy[0]+snapshot[0]+calls;
 end
endmodule
module top;
 wire[31:0] one,two;
 worker u(one),v(two);
endmodule
