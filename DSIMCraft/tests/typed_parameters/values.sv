`timescale 1ns/1ps
module top;
parameter int I=32'hxz123456;
localparam int unsigned U=32'hffffffff;
localparam byte B=8'b1xz001zx;
localparam byte unsigned UB=8'hf0;
localparam shortint S=-17;
localparam shortint unsigned US=16'hffff;
localparam longint L=-9;
localparam longint unsigned UL=64'hxz123456789abcde;
localparam bit[129:0] MASK=130'h3xz123456789abcdef0123456789abcdef;
localparam logic[79:0] FOUR=80'hxz123456789abcdef012;
localparam integer unsigned FOURINT=32'hxz123456;
localparam time T=64'hxz123456789abcde;
localparam bit FLAG=1'bx;
localparam logic signed[7:0] FOURNEG=-3;
localparam reg[3:0] NIBBLE=8'hfc;
reg signed[129:0]saved;
initial begin
saved=B;#1;$display("TRACE small %h %0d %0d %0d %0d %0d %h",I,U,B,UB,S,US,saved);
saved=L;$display("TRACE long %0d %0d %h %h",L,UL,MASK,saved);
$display("TRACE packed %h %h",FOURNEG,NIBBLE);
$display("TRACE four %h %h %h %h",FOUR,FOURINT,T,FLAG);#1;$finish;
end
endmodule
