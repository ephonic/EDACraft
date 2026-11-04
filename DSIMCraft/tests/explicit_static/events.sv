`timescale 1ns/1ps
module top;
integer q=0,done=0;
task automatic arm(input integer n);
 static event fired;
 static integer deliveries=0;
 fork
  begin @(fired);deliveries++;q+=deliveries;end
 join_none
 #n;->> fired;
 #1;wait fork;
 done++;
endtask
initial begin
 fork
  arm(2);
  begin #1;arm(4);end
 join
 $display("TRACE events %0d %0d",q,done);
 if(q!=3||done!=2)$fatal(1,"shared static event and automatic calls");
end
endmodule
