`timescale 1ns/1ps
module top;
localparam longint A=-64'sh123456789abcdef;
localparam longint Q=A/37;
localparam longint R=A%37;
localparam logic[129:0] BIG=130'h3fedcba9876543210123456789abcdef01;
localparam logic[129:0] QUOT=BIG/130'd257;
localparam logic[129:0] REM=BIG%130'd257;
localparam longint ZERO=9/0;
localparam integer FOUR=9/0;
localparam longint SHL=64'h123456789abcdef0<<64;
localparam longint SHR=64'h123456789abcdef0>>65;
localparam longint ASR=-64'sd17>>>65;
localparam bit[79:0] PAD=80'hxz123456789abcdef012<<32;
localparam logic[63:0] ALL=&130'h3ffffffffffffffffffffffffffffffff;
localparam logic[63:0] ANY=|130'd0;
localparam logic[7:0] ANDZ=&2'b1z;
localparam logic[7:0] ORZ=|2'b0z;
localparam logic[7:0] NOTZ=~2'b0z;
localparam logic[7:0] MUXZ=2'b0z ? 8'ha5 : 8'ha4;
reg[129:0]saved;
initial begin saved=QUOT;#1;saved=REM;
$display("TRACE div %h %h %h %h",Q,R,QUOT,REM);
$display("TRACE reductions %b %b %b %b %b %b",ALL,ANY,ANDZ,ORZ,NOTZ,MUXZ);
$display("TRACE zero %h %h",ZERO,FOUR);
$display("TRACE shift %h %h %h %h",SHL,SHR,ASR,PAD);#1;$finish;end
endmodule
