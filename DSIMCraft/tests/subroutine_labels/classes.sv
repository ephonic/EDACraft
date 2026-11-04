package p;
 class C #(parameter int N=3);
  int value;
  function new(input int x=N);value=x;endfunction : new
  static function int size();return N;endfunction : size
  virtual function int get();return value;endfunction : get
  task put(input int v);#1;value=v;endtask : put
 endclass : C
 class D extends C#(7);
  function new();int x;super.new(12);x=0;endfunction : new
  virtual function int get();return super.get()+1;endfunction : get
 endclass : D
 function automatic int inc(input int v);return v+1;endfunction : inc
endpackage : p
module leaf #(parameter int N=1)(output int observed);
 import p::*;
 C#(N) a;
 task automatic step(input int x);int y;y=inc(x);a.put(y);observed=a.get();endtask : step
 initial begin a=new();observed=a.get();step(N+10);end
endmodule
module top;
 import p::*;
 C#(7) base_handle;
 D derived_handle;
 int observed;
 wire[31:0] a,b;
 leaf #(4) u(a);leaf #(9) v(b);
 initial begin
  derived_handle=new();base_handle=derived_handle;
  observed=base_handle.get();$display("TRACE dispatch %0d %0d",observed,C#(7)::size());
  #2;$display("TRACE clones %0d %0d",a,b);$finish;
 end
endmodule
