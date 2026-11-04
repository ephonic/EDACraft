`timescale 1ns/1ps
module top;
  logic[3:0] a,b,en;logic all_en;
  wire[3:0] x,n,an,na,o,no,bf,nt,t0,t1,z0,z1,delayed;
  xor gx[3:0](x,a,b);xnor gn[0:3](n,a,b);
  and ga[-1:2](an,a,all_en);nand gna[5:2](na,a,b);
  or go[3:0](o,a,b);nor gno[3:0](no,a,b);
  buf gb[3:0](bf,a);not gi[3:0](nt,a);
  bufif0 gt0[3:0](t0,a,en);bufif1 gt1[0:3](t1,a,en);
  notif0 gz0[-1:2](z0,a,en);notif1 gz1[3:0](z1,a,en);
  buf #(1,2) gd[3:0](delayed,a);
  initial begin
    a=4'b1010;b=4'b1100;en=4'b0101;all_en=1;#3;
    $display("TRACE gates %b %b %b %b %b %b %b %b",x,n,an,na,o,no,bf,nt);
    if(x!==4'b0110||n!==4'b1001||an!==a||na!==4'b0111||o!==4'b1110||no!==4'b0001||bf!==a||nt!==4'b0101)$fatal(1,"logic array");
    $display("TRACE tri %b %b %b %b %b",t0,t1,z0,z1,delayed);
    if(t0!==4'b1z1z||t1!==4'bz0z0||z0!==4'b0z0z||z1!==4'bz1z1||delayed!==a)$fatal(1,"tri array");
    a=4'bzx01;b=4'b1010;en=4'bxxxx;all_en=0;#3;
    $display("TRACE unknown %b %b %b %b %b",x,an,bf,t0,delayed);
    if(an!==0||bf!==4'bxx01||delayed!==bf||t0!==4'bxxxx)$fatal(1,"unknown array");
    $finish;
  end
endmodule
