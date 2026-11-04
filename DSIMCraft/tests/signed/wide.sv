`timescale 1ns/1ps
module top;
 reg signed [79:0] a,b;
 reg signed [64:0] s;
 reg [79:0] u;
 reg [79:0] amount;
 reg c;
 wire signed [129:0] sum=a+b,product=a*b,quot=a/b,rem=a%b,ext=s,neg=-s,shift=a>>>amount;
 wire [129:0] mix=a+u,part=a[79:0];
 wire signed [129:0] choose=c?a:s;
 wire [7:0] compare={a<b,a<=b,a>b,a>=b,a==b,a!=b,a===b,a!==b};
 initial begin
  a=-80'sh123456789abcdef;b=80'sd127;s=-65'sd3;u=1;amount=67;c=0;
  #1 $display("TRACE wide %h %h %h %h",sum,product,quot,rem);
  $display("TRACE ext %h %h %h %h %h %h",ext,neg,shift,mix,part,choose);
  $display("TRACE dec %0d %0d %0d %b",a,quot,rem,compare);
  a=80'sh80000000000000000000;b=-1;amount=130;c=1;
  #1 $display("TRACE min %h %h %h %h",quot,rem,shift,choose);
  amount=80'h10000000000000000;
  #1 $display("TRACE large %h",shift);
  a=80'sbx;b=3;amount=1;
  #1 $display("TRACE x %b %b %b",quot,shift,compare);
  a=80'sbz;
  #1 $display("TRACE z %b %b",shift,ext);
 end
endmodule
