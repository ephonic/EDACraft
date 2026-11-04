module top;
  class State;int value=3;endclass
  State state;
  int observed;
  task automatic update(ref int value);
    value=7;#2;value=9;
  endtask
  initial begin
    state=new;
    fork
      update(state.value);
      begin #1;$display("TRACE scalar pending %0d",state.value);end
    join
    observed=state.value;
    $display("TRACE scalar output %0d",observed);
  end
endmodule
