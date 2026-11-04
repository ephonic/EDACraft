`timescale 1ns/1ps
module top;
integer total=0,i=0;
task automatic delayed(input integer ticks);
 integer values[];
 if(values.size()!=0)$fatal(1,"stale canceled storage");
 values=new[2];values[0]=4;#ticks;total+=values[0];
endtask
initial begin
 for(i=1;i<=12;i++)begin
  fork delayed(20);begin #1;end join_any
  disable fork;delayed(1);
 end
 $display("TRACE control %0d %0d",total,i);
 if(total!=48||i!=13)$fatal(1,"dynamic cancel/reuse");
end
endmodule
