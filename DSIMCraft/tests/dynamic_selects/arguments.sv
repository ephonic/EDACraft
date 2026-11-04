`timescale 1ns/1ps
module top;
 logic [15:0] a[];
 logic [15:0] q=0,r=0;
 integer calls=0;
 function automatic integer pos();calls++;return 4;endfunction
 task automatic edit(ref logic[15:0] x[]);
  x[0][pos()+:4]+=3;
  #1;x[0][15:12]=4'ha;
 endtask
 task automatic later(inout logic[15:0] x[]);
  x[0][3:0]=#1 4'hb;
  x[0][11-:4]=4'hc;
  #1;
 endtask
 initial begin
  a=new[1];a[0]=16'h1234;
  edit(a);q=a[0];
  later(a);r=a[0];
  $display("TRACE arguments %h %h %0d",q,r,calls);
  #1;$finish;
 end
endmodule
