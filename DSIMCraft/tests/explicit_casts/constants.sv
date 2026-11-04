`timescale 1ns/1ps
module top;
parameter int W=13;
localparam longint A=longint'(32'hffffffff+1);
localparam B=8'(16'h12ff);
localparam C=(W+1)'(-1);
localparam D=int'(8'b1xz001z1);
localparam E=integer'(8'b1xz001z1);
localparam F=130'(8'sh80);
localparam G=4'(32'hff)+4'(32'h2);
localparam H=signed'(8'hff);
localparam I=unsigned'(-1);
localparam J=byte'(8'hff);
localparam K=longint'(byte'(32'hff));
localparam L=logic'('1);
localparam M=bit'('x);
localparam N=8'('1);
localparam O=16'(8'(32'hffff));
logic [63:0] a,k;
logic [129:0] f;
logic [13:0] c;
logic [7:0] b,d,e,g,h,i,j,n,o;
logic l,m;
initial begin
 a=A;b=B;c=C;d=D;e=E;f=F;g=G;h=H;i=I;j=J;k=K;l=L;m=M;n=N;o=O;
 #1;$display("TRACE constants %h %h %h %h %b %h %h %0d %0d %h %h",A,B,C,D,E,F,G,H,I,N,O);$finish;
end
endmodule
