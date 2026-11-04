`timescale 1ns/1ps
module bank #(parameter N=4)(output [7:0] q);
 reg [7:0] mem[0:N-1];
 reg [2:0] i;
 assign q=mem[i];
 initial begin
  $readmemh("reverse.hex",mem,1,3);
  i=1;#1 i=2;#1 mem[i][3:0]=4'hf;#1 i='z;
 end
endmodule
module top;
 wire [7:0] a,b;
 reg bitmem[0:3];
 reg [2:0] i;
 reg seen;
 bank u(a);
 bank v(b);
 generate for(genvar g=0;g<2;g=g+1)begin: row
  reg [7:0] mem[0:2];
  initial begin mem[0]=g;mem[1]=g+1;#2 mem[g]=8'hbc;end
 end endgenerate
 initial begin
  seen=0;bitmem[2]=0;i=2;
  #1 bitmem[i]=1;
  #1 $display("TRACE scalar %b seen=%b",bitmem[i],seen);
  i=7;bitmem[i]=0;
  #2 $display("TRACE outside %b",bitmem[i]);
 end
 initial begin @(posedge bitmem[2]) seen=1;end
endmodule
