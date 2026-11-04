`timescale 1ns/1ps
module top;
integer i=0,k=0,q=0;
initial begin
 for(k=0;k<50;k++)begin
  for(i=0;i<3;i++)fork #1 q++;join_none
  wait fork;
 end
 $display("TRACE recycle %0d %0t",q,$time);
 if(q!=150)$fatal(1,"lost reused activation");
 #1;$finish;
end
endmodule
