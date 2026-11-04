`timescale 1ns/1ps
module child #(parameter int P=3,parameter byte B=-1,parameter longint unsigned L=64'hffffffffffffffff,parameter bit[79:0] MASK='1)(output signed[63:0]q,output[79:0]m);
localparam int NEXT=P+1;
localparam byte SMALL=B;
assign q=P+L+NEXT+SMALL;assign m=MASK;
endmodule
module body(output signed[63:0]q);
parameter longint V=-5;localparam int N=V+3;assign q=V+N;
endmodule
module top;
wire signed[63:0]a,b,c,d,e;wire[79:0]ma,mb,mc;
child u(a,ma);
child #(.P(32'hxz000002),.B(8'hxz),.L(32'hffffffff),.MASK(80'hxz123456789abcdef012))v(b,mb);
child #(-7,8'h80,-3,80'hx)v2(c,mc);
body w(d);body #(.V(32'hfffffffd))w2(e);
initial begin #1;$display("TRACE overrides %h %h %h %h %h",a,b,c,d,e);$display("TRACE masks %h %h %h",ma,mb,mc);#1;$finish;end
endmodule
