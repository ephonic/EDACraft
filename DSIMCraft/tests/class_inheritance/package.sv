`timescale 1ps/1ps
package objects;
 class Base;
  int n=4;
  virtual function int get();return n;endfunction
 endclass
 class Derived extends Base;
  int other=9;
  function int get();return n+other;endfunction
 endclass
 function automatic int read_object(Base obj);return obj.get();endfunction
endpackage
module top;
 import objects::*;
 Base b;Derived d;int observed;
 initial begin d=new;b=d;observed=read_object(d);$display("TRACE package value=%0d field=%0d eq=%0d",observed,b.n,b==d);#2;$finish;end
endmodule
