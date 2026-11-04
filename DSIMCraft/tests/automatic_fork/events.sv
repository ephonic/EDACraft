`timescale 1ns/1ps
module top;
integer k=0,q=0,direct=0,level=0;
task automatic direct_wait(input integer n);
 reg local_clock=0;
 fork
  begin #1;local_clock=1;end
  begin @(posedge local_clock);direct+=n;end
 join
endtask
task automatic launch(input integer n);
 reg clock=0,allow=0;
 fork
  begin #1;clock=1;#1;allow=1;#1;clock=0;#1;clock=1;end
  begin @(posedge (clock&1) iff allow);q+=n;end
  direct_wait(n);
  begin wait(allow);level+=n;end
 join_none
endtask
initial begin
 for(k=1;k<=4;k++)launch(k);
 #1; $display("TRACE events early %0d %0d %0d",q,direct,level);
 wait fork;
 $display("TRACE events done %0d %0d %0d",q,direct,level);
 if(q!=10||direct!=10||level!=10)$fatal(1,"frame subscription");
 $finish;
end
endmodule
