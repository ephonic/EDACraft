`timescale 1ns/1ps
module top;
integer a[2:1],i=0;
task automatic delayed(inout integer values[],input integer ticks);#ticks;values[0]++;endtask
initial begin
 a[2]=0;a[1]=1;
 for(i=1;i<=12;i++)begin
  fork delayed(a,20);begin #1;end join_any
  disable fork;delayed(a,1);
 end
 $display("TRACE control %0d %0d %0d",a[2],a[1],i);
 if(a[2]!=12||a[1]!=1||i!=13)$fatal(1,"unsized cancel/reuse");
end
endmodule
