`timescale 1ns/1ps
module top;
integer x[0:1],i=0;
task automatic delayed(ref integer a[2],input integer amount,input integer ticks);#ticks;a[0]+=amount;a[1]+=2*amount;endtask
initial begin
 x[0]=0;x[1]=0;
 for(i=1;i<=12;i++)begin
  fork delayed(x,1000,20);#1;join_any
  disable fork;delayed(x,i,1);
 end
 $display("TRACE control %0d %0d %0d",x[0],x[1],i);
 if(x[0]!=78||x[1]!=156||i!=13)$fatal(1,"array reference cancellation");
end
endmodule
