`timescale 1ns/1ps
module top;
 reg [7:0] a[2:11];
 reg [7:0] b[11:2];
 reg [79:0] w[0:2];
 reg [3:0] i,start,finish;
 wire [7:0] q=a[i];
 wire [79:0] a_state={a[11],a[10],a[9],a[8],a[7],a[6],a[5],a[4],a[3],a[2]};
 wire [79:0] b_state={b[11],b[10],b[9],b[8],b[7],b[6],b[5],b[4],b[3],b[2]};
 wire [239:0] w_state={w[2],w[1],w[0]};
 initial begin
  i=2;start=8;finish=6;
  $readmemh("init.hex",a);
  $readmemb("init.bin",b);
  $readmemh("wide.hex",w);
  #1 $display("TRACE hex %h %h %h %h %h %h %h",a[2],a[3],a[4],a[5],a[6],a[7],a[9]);
  $display("TRACE bin %b %b %b %b",b[2],b[3],b[5],b[6]);
  $display("TRACE wide %h %h %h",w[0],w[1],w[2]);
  $readmemh("reverse.hex",a,start,finish);
  #1 $display("TRACE reverse %h %h %h",a[8],a[7],a[6]);
  i=7;
  #1 $display("TRACE q %h",q);
  $finish;
 end
endmodule
