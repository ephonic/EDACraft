`timescale 1ns/1ps
package forward_types;
 typedef class Child;
 typedef Child#(logic[64:0],65) Early;
 typedef Child#(.T(logic[64:0]),.W(65)) Same;
 class Base#(type T=int,parameter int W=8);
  T value;logic[W-1:0] lane;
  function new(T n);value=n;lane='1;endfunction
  virtual function T get();return value;endfunction
  function int width_n();return $bits(lane);endfunction
 endclass
 class Child#(type T=int,parameter int W=8) extends Base#(T,W);
  function new(T n);super.new(n);endfunction
  virtual function T get();return value+1;endfunction
 endclass
 typedef Child#(logic[64:0],65) Late;
 function automatic Early pass(ref Same value);return value;endfunction
endpackage
module top;
 forward_types::Early a;forward_types::Same b;forward_types::Late c;
 forward_types::Base#(logic[64:0],65) base;
 logic[64:0] observed;int width_n,identity;
 initial begin
  a=new(65'h1fffffffffffffffe);b=a;c=forward_types::pass(b);base=c;
  observed=base.get();width_n=base.width_n();identity=(a==c);
  #1;$display("TRACE forward %h %0d %0d",observed,width_n,identity);
 end
endmodule
