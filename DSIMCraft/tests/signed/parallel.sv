`timescale 1ns/1ps
module lane #(parameter K=1)(output signed [15:0] out);
 reg signed [7:0] a,b;
 reg signed [7:0] mem[0:3];
 reg [2:0] i;
 assign out=mem[i]+(a>>>2);
 initial begin
  a=-12;b=K;i=0;mem[0]=-1;mem[1]=-2;mem[2]=-3;mem[3]=-4;
  repeat(4)begin #2 mem[i]<=#1 a/b;a=a+b;i=i+1;end
 end
endmodule
module top;
 wire signed [15:0] a,b;
 lane #(.K(3)) u(a);
 lane #(.K(5)) v(b);
endmodule
