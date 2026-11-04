`timescale 1ns/1ps
module top;integer q=0,bad=0,k=0,n=0;
initial begin for(k=0;k<3;k++)begin
 fork begin #1;q=q+1;end begin n<=#5 k+11;#20;bad=bad+1;end join_any
 disable fork;wait fork;
end #10;$display("TRACE cancel %0d %0d %0d %0t",q,bad,n,$time);
if(q!==3||bad!==0||n!==13)$fatal(1,"cancel mismatch");$finish;end endmodule
