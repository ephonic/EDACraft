`timescale 1ns/1ps
module top;
integer i=0,q=0,bad=0,n=0;
initial begin
 begin : outer
  for(i=0;i<4;i++)fork begin n<=#5 11;#1;disable outer;end #10 bad++;join_none
  #20;bad++;
 end
 wait fork;
 $display("TRACE cancel %0d %0t",bad,$time);
 for(i=0;i<3;i++)fork #1 q++;#10 bad++;join_none
 #2;disable fork;wait fork;
 #5;$display("TRACE reuse %0d %0d %0d %0t",q,bad,n,$time);
 if(q!=3||bad!=0||n!=11)$fatal(1,"cancellation or NBA lost");
 $finish;
end
endmodule
