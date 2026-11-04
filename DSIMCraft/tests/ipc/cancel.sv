`timescale 1ps/1ps
module top;
 mailbox #(int) box=new(1);
 semaphore keys=new(0),cancelled_keys=new(0);
 int small_at,bad,value;
 initial begin
  fork
   begin : heavy
    fork
     begin keys.get(3);bad++;end
     begin #2;disable heavy;end
    join
   end
   begin #1;keys.get();small_at=$time;end
   begin #3;keys.put();end
  join
  #1;if(small_at!=3)bad++;
  box.put(10);
  fork box.put(20);join_none
  #1;disable fork;
  box.get(value);if(value!=10||box.num()!=0)bad++;
  fork box.get(value);join_none
  #1;disable fork;
  box.put(30);if(box.num()!=1)bad++;
  box.get(value);
  fork
   begin cancelled_keys.get(2);bad++;end
   begin #1;cancelled_keys.get();bad++;end
  join_none
  #2;disable fork;
  cancelled_keys.put();if(cancelled_keys.try_get()!=1)bad++;
  $display("TRACE cancel %0d %0d %0d",small_at,value,bad);
  $finish;
 end
endmodule
