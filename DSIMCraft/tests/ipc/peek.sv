`timescale 1ps/1ps
module top;
 mailbox #(int) box=new;
 int a,b,c,bad;
 initial begin
  fork
   box.peek(a);
   begin #1;box.peek(b);end
   begin #2;box.get(c);end
   begin #3;box.put(81);end
  join
  if(a!=81||b!=81||c!=81||box.num()!=0)bad++;
  $display("TRACE peek %0d %0d %0d %0d",a,b,c,bad);$finish;
 end
endmodule
