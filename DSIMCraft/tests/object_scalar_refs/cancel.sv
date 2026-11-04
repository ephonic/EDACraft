module top;
 class State;int value=3;endclass
 State state;int observed;
 task automatic change(ref int value);value=7;#4;value=9;endtask
 initial begin state=new;fork change(state.value);join_none #1;disable fork;#5;
  observed=state.value;$display("TRACE cancel ref %0d",observed);
 end
endmodule
