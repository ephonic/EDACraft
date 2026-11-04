module top;
 class State;logic[95:0] bits;int number;string text="A";real amount=1.25;endclass
 State state;int observed;
 function automatic void update(ref logic[95:0] bits,ref int number,ref string text,ref real amount);
  bits=96'h123456789abcdef000000000;bits[3:0]=4'bxz01;
  number='x;text={text,"B"};amount=amount*2.0;
 endfunction
 initial begin state=new;update(state.bits,state.number,state.text,state.amount);observed=state.number;
  $display("TRACE values %h %0d %s %0.2f",state.bits,observed,state.text,state.amount);
 end
endmodule
