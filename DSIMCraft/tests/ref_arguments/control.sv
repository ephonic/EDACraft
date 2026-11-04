`timescale 1ns/1ps
module top;
integer x=0,i=0;
task automatic delayed(ref integer a,input integer amount,input integer ticks);
 #ticks;a+=amount;
endtask
initial begin
 for(i=1;i<=12;i++)begin
  fork
   delayed(x,1000,20);
   begin #1;end
  join_any
  disable fork;
  delayed(x,i,1);
 end
 $display("TRACE control %0d %0d",x,i);
 if(x!=78||i!=13)$fatal(1,"ref cancellation and slot reuse");
end
endmodule
