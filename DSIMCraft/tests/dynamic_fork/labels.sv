`timescale 1ns/1ps
module top;
integer i=0,q=0,bad=0;
initial begin
 for(i=0;i<3;i++)fork begin
  begin : guard
   #1;disable guard;#10;bad++;
  end
  q++;
 end join_none
 wait fork;
 $display("TRACE labels %0d %0d %0t",q,bad,$time);
 if(q!=3||bad!=0)$fatal(1,"cloned named target lost");
 #1;$finish;
end
endmodule
