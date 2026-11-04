`timescale 1ps/1ps
module top;
 mailbox #(int) box=new(1);
 semaphore keys=new;
 int observed,awoken;
 initial begin
  box.put(3);box.get(observed);box.get(observed);box.get(observed);
  #2;$display("TRACE rollback %0d %0d",observed,awoken);$finish;
 end
 initial begin keys.get();awoken=1;end
 initial begin #2;box.put(9);keys.put();#1;box.put(7);end
endmodule
