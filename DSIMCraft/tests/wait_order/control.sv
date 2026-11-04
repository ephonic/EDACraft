`timescale 1ns/1ps
module top;
event a,b;
integer hits=0,misses=0,bad=0,i=0;
task automatic launch(input integer amount);
 fork
  begin wait_order(a,b) hits+=amount;else misses++;end
 join_none
endtask
task automatic canceled;
 fork
  begin wait_order(a,b) bad++;else bad+=100;end
  begin #1;end
 join_any
 disable fork;
endtask
initial begin
 for(i=1;i<=12;i++)begin
  launch(i);
  #1;->a;#1;->b;
  #1;wait fork;
  canceled();
  ->b;->a;
  #1;
 end
 $display("TRACE control %0d %0d %0d",hits,misses,bad);
 if(hits!=78||misses!=0||bad!=0)$fatal(1,"ordered clone reuse/cancellation");
end
endmodule
