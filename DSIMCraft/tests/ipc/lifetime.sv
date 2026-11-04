`timescale 1ps/1ps
module top;
 mailbox #(int) box=new;
 int values[2],index,selector_calls,bad;
 function automatic int select();selector_calls++;return index;endfunction
 task automatic receive(input int lane);
  int local_value;
  box.get(local_value);values[lane]=local_value;
 endtask
 initial begin
  fork
   begin box.get(values[select()]);end
   begin #1;index=1;box.put(71);end
  join
  if(values[0]!=71||values[1]!=0||selector_calls!=1)bad++;
  fork
   receive(0);
   begin #1;receive(1);end
   begin #2;box.put(11);box.put(22);end
  join
  if(values[0]!=11||values[1]!=22)bad++;
  box.put(33);receive(1);
  $display("TRACE lifetime %0d %0d %0d %0d",values[0],values[1],selector_calls,bad);
  $finish;
 end
endmodule
