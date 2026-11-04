`timescale 1ns/1ps
module top;
integer i=0,q=0,r=0;
initial begin
 for(i=0;i<3;i++)begin
  fork begin #1;q++;fork #4 r++;join_none end join_none
  wait fork;
 end
 $display("TRACE direct %0d %0d %0t",q,r,$time);
 #7;$display("TRACE nested %0d %0d %0t",q,r,$time);
 if(q!=3||r!=3)$fatal(1,"lost orphaned grandchild");
 $finish;
end
endmodule
