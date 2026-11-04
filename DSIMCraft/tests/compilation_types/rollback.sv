`timescale 1ps/1ps
class State;
 static int count=3;
 int values[$];
 function new();values.push_back(3);endfunction
 function void update(int n);count=n;values.push_back(n);endfunction
endclass
module observer(output int seen);
 always @(State::count) seen=State::count;
endmodule
module top;
 State value;int observed,seen;
 observer o(seen);
 initial begin
  value=new;observed=State::count;
  #2;value.update(3);observed=value.values[$];
  #1;value.update(9);observed=value.values[$];
  #1;
  if(value.values.size()!=3||State::count!=9||seen!=9)$fatal(1,"global heap/static event state");
  $display("TRACE unit rollback %0d %0d %0d",observed,seen,value.values.size());
 end
endmodule
