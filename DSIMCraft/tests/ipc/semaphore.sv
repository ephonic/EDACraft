`timescale 1ps/1ps
module top;
 semaphore keys=new(1),fifo=new(0);
 int big_at,small_at,bad,ready;
 initial begin
  fork
   begin keys.get(2);big_at=$time;end
   begin #1;keys.get();small_at=$time;end
   begin #2;if(big_at!=0||small_at!=1)bad++;keys.put();#1;keys.put();end
  join
  if(big_at!=3||small_at!=1||keys.try_get()!=0)bad++;
  keys.put(3);if(keys.try_get(2)!=1||keys.try_get()!=1||keys.try_get()!=0)bad++;
  // Both calls are already suspended before a single key is returned.
  fork
   begin fifo.get(2);if($time!=7)bad++;end
   begin #1;fifo.get();if($time!=5)bad++;end
   begin #2;fifo.put();#1;fifo.put();#1;fifo.put();end
  join
  keys.get(0);ready=1;
  $display("TRACE semaphore %0d %0d %0d %0d",big_at,small_at,ready,bad);
  $finish;
 end
endmodule
