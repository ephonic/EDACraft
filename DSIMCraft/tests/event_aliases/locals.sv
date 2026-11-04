module top;
 int hits=0,stage=0;
 task automatic one(input int delta);
  event local_event;
  fork
   begin @(local_event);hits+=delta;end
   begin #1;->local_event;end
  join
 endtask
 initial begin
  fork one(1);one(10);join
  stage++;#1;$display("TRACE locals %0d",hits);$finish;
 end
 initial begin #10;$fatal(1,"local events shared or lost");end
endmodule
