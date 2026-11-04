module top;
 typedef struct {bit[3:0] clean;logic[3:0] state;string text;} pair_t;
 class State;pair_t value;endclass
 State state;int observed;
 function automatic void update(ref pair_t value);
  value='{4'bxxxx,4'bxz01,"A"};value.text={value.text,"B"};
 endfunction
 initial begin state=new;update(state.value);observed=state.value.clean;
  $display("TRACE aggregate %0d %b %s",observed,state.value.state,state.value.text);
 end
endmodule
