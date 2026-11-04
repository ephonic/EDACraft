`timescale 1ps/1ps
module top;
 typedef class Right;
 class Left;
  Right peer;
  function Right pass(Right value);return value;endfunction
  task change(ref Right target, input Right value);target=value;endtask
 endclass
 typedef Right Alias;
 class Right;
  Left peer;
  int value=13;
  function Left back();return peer;endfunction
 endclass
 Left l;Right r;Alias chosen;int observed;
 initial begin
  l=new;r=new;l.peer=r;r.peer=l;
  l.change(chosen,l.pass(r));observed=chosen.value;
  #1;$display("TRACE signatures %0d %0d %0d",observed,l.peer==chosen,r.back()==l);
 end
endmodule
