`timescale 1ns/1ps
module context_cell #(parameter longint P=32'hffffffff+32'd1)(output[63:0]q);assign q=P;endmodule
module top;
localparam longint SUM=32'hffffffff+32'd1;
localparam longint SHIFT=1<<40;
localparam longint NEG=-32'sh80000000;
localparam byte signed SMALL=-1;
localparam longint MIX=SMALL+8'd1;
localparam longint SIGNED_SUM=SMALL+8'sd1;
localparam longint SELECT=1?(32'hffffffff+1):0;
localparam logic[79:0] WIDE='1;
localparam bit[79:0] CLEAN='x;
localparam signed INFER=-8'sd2;
localparam logic signed[79:0] MUX=1'bx ? 80'hxz123456789abcdef012 : 80'hxz123456789abcdeff12;
localparam longint PRED=(32'shffffffff<64'd1)?(32'hffffffff+1):0;
localparam longint RED=~(32'hffffffff+1);
wire[63:0]a,b;
context_cell u(a);context_cell #(.P(32'hffffffff+32'd2))v(b);
initial begin #1;
$display("TRACE context %h %h %h %h %h %h",SUM,SHIFT,NEG,MIX,SIGNED_SUM,SELECT);
$display("TRACE predicates %h %h %h %h",INFER,MUX,PRED,RED);
$display("TRACE widths %h %h %h %h",a,b,WIDE,CLEAN);#1;$finish;end
endmodule
