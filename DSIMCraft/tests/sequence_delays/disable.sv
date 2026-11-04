`timescale 1ns/1ps
module top;
reg clk=0,a=1,b=0,c=1,d=1,rst=0;integer tick=0,pass=0,fail=0,cov=0,other=0;
always #5 clk=~clk;
ap:assert property(@(posedge clk) disable iff(rst) a |-> ##3 b ##1 c) pass=pass+1;else fail=fail+1;
cp:cover property(@(posedge clk) disable iff(rst) a |-> ##3 b ##1 c) cov=cov+1;
initial begin #18;rst=1;#1;rst=0;#25;rst<=1;#3;rst=0;#31;rst=1;#1;rst=0;end
initial begin
 #2;
 repeat(12)begin
  #5;$display("TRACE counts %0d %0d %0d %0d %0d",tick,pass,fail,cov,other);
  #5;tick=tick+1;a=(tick%4!=2);b=(tick%3!=0);c=(tick%5!=1);d=(tick%4!=0);
 end
 #1;$finish;
end
endmodule
