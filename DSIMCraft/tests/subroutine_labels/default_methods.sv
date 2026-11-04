package defaults_pkg;
 function automatic int inc(int x,int y=x+2);return y;endfunction : inc
 class Base #(parameter int N=4);
  int bias=3,value;
  function new(int a=N,int b=a+1);value=b;endfunction : new
  virtual function int get(int a,int b=inc(a)+bias);return b+value;endfunction : get
  function int helper(int x);return x+bias;endfunction : helper
  function int nested(int a,int b=helper(a));return b;endfunction : nested
  virtual task put(int a,int b=a+bias);#1;value=b;endtask : put
 endclass
 class Derived extends Base#(7);
  function new(int a=9,int b=a+1);super.new(a,b);endfunction : new
  virtual function int get(int a,int b=a+100);return b+value+10;endfunction : get
  virtual task put(int a,int b=a+100);#1;value=b+10;endtask : put
 endclass
endpackage
module leaf #(parameter int N=1)(output int observed);
 import defaults_pkg::*;
 Base#(N) obj;
 initial begin obj=new();observed=obj.get(N);end
endmodule
module top;
 import defaults_pkg::*;
 Base#(7) base_handle;Derived derived_handle;
 wire[31:0] one,two;
 leaf#(4) u(one);leaf#(9) v(two);
 int observed;
 initial begin
  derived_handle=new();base_handle=derived_handle;
  observed=base_handle.get(5);
  $display("TRACE defaults methods %0d %0d %0d",observed,derived_handle.get(5),base_handle.nested(6));
  #1;$display("TRACE defaults clones %0d %0d",one,two);
  base_handle.put(8);$display("TRACE defaults virtual task %0d",base_handle.value);$finish;
 end
endmodule
