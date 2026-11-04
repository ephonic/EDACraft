`timescale 1ns/1ps
module top;
integer i=0,q=0,r=0,seen=0;
initial begin
 for(i=0;i<5;i++)fork begin #1;q++;seen+=i;end #3 r++;join_none
 wait fork;
 $display("TRACE burst %0d %0d %0d %0t",q,r,seen,$time);
 if(q!=5||r!=5||seen!=25)$fatal(1,"lost overlapping branch");
 #1;$finish;
end
endmodule
