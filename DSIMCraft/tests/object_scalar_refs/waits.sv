module top;
 class State;int value=3;endclass
 State state;int observed;
 task automatic await_value(const ref int value);wait(value==7);observed=value;endtask
 task automatic change(ref int value);#2;value=9;endtask
 initial begin
  state=new;
  fork
   await_value(state.value);
   begin #1;state.value=7;end
  join
  $display("TRACE ref wait %0d %0d",observed,state.value);
  fork
   change(state.value);
   begin wait(state.value==9);observed=state.value;end
  join
  $display("TRACE field wait %0d %0d",observed,state.value);
 end
endmodule
