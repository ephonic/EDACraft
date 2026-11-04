`timescale 1ps/1ps
module top;
 mailbox #(int) box=new(1);
 int first,second,third,peeked,sent_at,bad,observed;
 initial begin
  box.put(10);
  if(box.num()!=1||box.try_put(99)!=0)bad++;
  fork
   begin #1;box.put(20);sent_at=$time;box.put(30);end
   begin
    #2;box.peek(peeked);if(peeked!=10||box.num()!=1)bad++;
    box.get(first);observed=first;
    #1;box.get(second);observed=second;
    #1;box.get(third);observed=third;
   end
  join
  if(first!=10||second!=20||third!=30||sent_at!=2||box.num()!=0)bad++;
  if(box.try_get(first)!=0||first!=10)bad++;
  if(box.try_put(40)!=1||box.try_peek(peeked)!=1||peeked!=40||box.num()!=1)bad++;
  box.get(first);
  $display("TRACE mailbox %0d %0d %0d %0d %0d",first,second,third,sent_at,bad);
  $finish;
 end
endmodule
