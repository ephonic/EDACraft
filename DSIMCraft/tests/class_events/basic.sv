`timescale 1ps/1ps
module top;
 class Waiter;
  event trigger;
  task notify();->trigger;endtask
 endclass
 Waiter waiter;int hits=0;
 initial begin
  waiter=new;
  fork
   begin @(waiter.trigger);hits++;end
   begin #2;waiter.notify();end
  join
  if(hits!=1)$fatal(1,"instance event");
  $display("TRACE class event %0d",hits);$finish;
 end
endmodule
