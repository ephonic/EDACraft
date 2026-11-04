module top;
 int count=1,hits=0,changes=0,stage=0;string word="x";
 initial begin
  fork
   begin wait({count{word}}=="xxx");hits++;end
   begin @({count{word}});changes++;end
   begin #1;count=3;end
  join
  stage++;#1;$display("TRACE waits %0d %0d",hits,changes);$finish;
 end
 initial begin #10;$fatal(1,"replication sensitivity lost");end
endmodule
