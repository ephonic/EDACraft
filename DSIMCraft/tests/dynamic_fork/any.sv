`timescale 1ns/1ps
module top;
integer i=0,q=0,r=0;
initial begin
 for(i=0;i<3;i++)fork #1 q++;#5 r++;join_any
 $display("TRACE first %0d %0d %0t",q,r,$time);
 wait fork;
 $display("TRACE any %0d %0d %0t",q,r,$time);
 if(q!=3||r!=3)$fatal(1,"lost join_any branch");
 #1;$finish;
end
endmodule
