module top;
 class State;int value=3;endclass
 State state;int observed;
 function automatic int add(ref int value,input int depth);
  value++;
  if(depth>0)return add(value,depth-1)+value;
  return value;
 endfunction
 initial begin state=new;observed=add(state.value,2);$display("TRACE recursive ref %0d %0d",observed,state.value);end
endmodule
