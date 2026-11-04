`timescale 1ns/1ps
module top;
 logic[15:0] a[];
 logic[7:0] q=0;
 logic[15:0] observed=0;
 task automatic edit(ref logic[15:0] x[],output logic[7:0] tail);
  {x[0][7:4],tail}=12'habc;
  #1;{x[0][3:0],tail[3:0]}=8'hde;
 endtask
 task automatic later(inout logic[15:0] x[],output logic[7:0] tail);
  {x[0],tail}=#1 24'h56789a;
  #1;
 endtask
 initial begin
  a=new[1];a[0]=16'h1234;edit(a,q);
  observed=a[0];$display("TRACE ref %h %h",observed,q);
  later(a,q);observed=a[0];$display("TRACE inout %h %h",observed,q);
  #1;$finish;
 end
endmodule
