`timescale 1ns/1ps
module top;
 reg signed [3:0] a,b;
 reg [4:0] u;
 reg [2:0] shift;
 reg [4:0] i,j;
 wire signed [7:0] add=a+b,sub=a-b,mul=a*b,quot=a/b,rem=a%b,neg=-a,shr=a>>>shift;
 wire [7:0] forced=(a+b)+u,cast=$signed(a+b)+u;
 wire [7:0] rel={a<b,a<=b,a>b,a>=b,a==b,a!=b,a===b,a!==b};
 initial begin
  for(i=0;i<16;i=i+1)begin
   for(j=0;j<16;j=j+1)begin
    a=i;b=j;u=j+16;shift=j;
    #1 $display("TRACE %h %h %h %h %h %h %h %h %h %h",add,sub,mul,quot,rem,neg,shr,forced,cast,rel);
   end
  end
 end
endmodule
