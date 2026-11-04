module top;
 class Counter;
  static int count=0;
  extern static function int bump(input int n=2);
 endclass
 function int Counter::bump(input int n);count+=n;return count;endfunction
 int observed=0;
 initial begin
  observed=Counter::bump();
  #2;observed=Counter::bump(3);$display("TRACE count %0d",observed);
  #2;observed=Counter::bump(7);$display("TRACE count %0d",observed);
  #2;observed=Counter::bump(1);$display("TRACE final %0d",observed);$finish;
 end
endmodule
