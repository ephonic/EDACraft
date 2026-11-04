`timescale 1ps/1ps
package types;
 virtual class Proto;
  pure virtual function string kind();
 endclass
 class Impl extends Proto;
  function string kind();return "impl";endfunction
 endclass
endpackage
module unit_test #(parameter W=8)(output logic[W-1:0] observed,output int result);
 virtual class Base;
  pure virtual function logic[W-1:0] get(input logic[W-1:0] value);
 endclass
 virtual class Mid extends Base;
  pure virtual function logic[W-1:0] get(input logic[W-1:0] renamed);
 endclass
 class Derived extends Mid;
  function logic[W-1:0] get(input logic[W-1:0] renamed);return renamed^'1;endfunction
 endclass
 Base b;Derived d,e;
 initial begin d=new;b=d;result=$cast(e,b);observed=b.get(1);end
endmodule
module top;
 import types::*;
 wire[7:0] a;wire[128:0] b;wire[31:0] ra,rb;
 unit_test #(8) one(a,ra);unit_test #(129) two(b,rb);
 Proto p;Impl i,j;int ok;
 initial begin
  i=new;p=i;ok=$cast(j,p);
  #2;$display("TRACE clones %h %h %0d %0d %0d %s",a,b,ra,rb,ok,j.kind());$finish;
 end
endmodule
