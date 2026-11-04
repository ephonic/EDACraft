`timescale 1ns/1ps
module forward_lane #(parameter int W=8)(output logic[W-1:0] observed);
 typedef class Child;
 typedef Child#(logic[W-1:0]) Early;
 class Base#(type T=int);
  T value;
  function new(T n);value=n;endfunction
  virtual function T get();return value;endfunction
 endclass
 class Child#(type T=int) extends Base#(T);
  Child#(T) peer;
  function new(T n);super.new(n);endfunction
  virtual function T get();return value^3;endfunction
 endclass
 Early a;Child#(logic[W-1:0]) b;Base#(logic[W-1:0]) base;
 initial begin a=new('1);b=a;b.peer=a;base=b.peer;observed=base.get();end
endmodule
module top;
 wire[64:0] one;wire[128:0] two;
 forward_lane #(65) a(one);forward_lane #(129) b(two);
 initial begin #1;$display("TRACE forward clones %h %h",one,two);end
endmodule
