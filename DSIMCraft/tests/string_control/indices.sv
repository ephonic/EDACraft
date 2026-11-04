`timescale 1ns/1ps
module top;
 string s="abcd";integer i=0,sum=0;logic [63:0] huge=64'h0000000100000001;
 initial begin
  for(i=0;i<4;i++)sum=sum+s[i];
  $display("TRACE sum %0d %h %h %0d",sum,s[huge],s[-1],$bits(s[1]));
  s[0]="Z";s[3]=16'h5141;s[8]=8'h51;s[-1]=8'h52;
  $display("TRACE write [%s]",s);
  #1;$finish;
 end
endmodule
