`timescale 1ns/1ps
module top;
reg clk=0,a=1,b=0,c=1,d=1,rst=0;integer tick=0,pass=0,fail=0,cov=0,other=0;
always #5 clk=~clk;
ap:assert property(@(posedge clk) a |-> b ##2 c ##0 d ##1 b) pass=pass+1;else fail=fail+1;
cp:cover property(@(posedge clk) a |-> b ##2 c ##0 d ##1 b) cov=cov+1;
np:assert property(@(posedge clk) a |=> b ##1 c) other=other+1;else ;
initial begin
 #2;
 repeat(12)begin
  #5;$display("TRACE counts %0d %0d %0d %0d %0d",tick,pass,fail,cov,other);
  #5;tick=tick+1;a=(tick%4!=2);b=(tick%3!=0);c=(tick%5!=1);d=(tick%4!=0);
 end
 #1;$finish;
end
endmodule
