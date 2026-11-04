`timescale 1ns/1ps
module top;
integer x=0,i=0,total=0;
task automatic delayed(const ref integer a,input integer ticks,output integer result);#ticks;result=a;endtask
initial begin
 for(i=1;i<=12;i++)begin
  fork delayed(x,20,total);begin #1;end join_any
  disable fork;
  x=i;delayed(x,1,total);
 end
 $display("TRACE control %0d %0d %0d",x,i,total);
 if(x!=12||i!=13||total!=12)$fatal(1,"const ref cancel/reuse");
end
endmodule
