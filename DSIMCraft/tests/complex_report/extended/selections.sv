`timescale 1ns/1ps
module tb;
  parameter integer DEPTH=37;
  parameter logic [15:8] P=8'hab;
  parameter logic [0:7] A=8'hc3;
  localparam logic[3:0] D=DEPTH[3:0];
  localparam logic[3:0] U=P[8+:4],V=P[15-:4];
  localparam logic[3:0] B=A[0+:4],C=A[7-:4];
  wire [7:0] gv[0:3];
  genvar g;generate for(g=0;g<4;g++)begin:x assign gv[g]=g[7:0];end endgenerate
  integer i;
  initial begin
    #1; // Let generated continuous drivers settle before reading their nets.
    if(D!==5||U!==4'hb||V!==4'ha||B!==4'hc||C!==4'h3)$fatal(1,"constant selects %h %h %h %h %h",D,U,V,B,C);
    for(i=0;i<4;i++)if(gv[i]!==i[7:0])$fatal(1,"genvar select");
    i=8;if(P[i+:4]!==4'hb)$fatal(1,"dynamic param select");
    i=0;if(A[i+:4]!==4'hc)$fatal(1,"ascending param select");
    i=7;if(A[i-:4]!==4'h3)$fatal(1,"ascending indexed select");
    i=31;if(DEPTH[i]!==0)$fatal(1,"bit select");
    i=99;if(P[i]!==1'bx||DEPTH[99]!==1'bx)$fatal(1,"out of range select");
    $display("TRACE selects %h %h %h %h %h",D,U,V,B,C);$finish;
  end
endmodule
