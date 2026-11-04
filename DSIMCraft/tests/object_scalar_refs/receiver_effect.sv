module top;
 class State;int value=3;endclass
 State state,original,other;int calls,observed;
 function automatic State pick();calls++;return state;endfunction
 task automatic update(ref int a,ref int b);a=7;#2;b=a+2;endtask
 initial begin
  state=new;original=state;other=new;other.value=20;
  fork
   update(pick().value,original.value);
   begin #1;state=other;original.value=11;$display("TRACE alias pending %0d %0d %0d",original.value,state.value,calls);end
  join
  observed=original.value;
  $display("TRACE aliases %0d %0d %0d",observed,state.value,calls);
 end
endmodule
