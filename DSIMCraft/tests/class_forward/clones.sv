`timescale 1ps/1ps
module unit_test #(parameter W=8)(output logic[W-1:0] observed);
 typedef class Derived;
 virtual class Base;
  Derived peer;
  pure virtual function logic[W-1:0] get();
 endclass
 class Derived extends Base;
  logic[W-1:0] bits='1;
  function logic[W-1:0] get();return bits^W'(3);endfunction
 endclass
 typedef Derived Alias;
 Alias d=new;Base b;Derived selected;int ok;
 initial begin
  b=d;ok=$cast(selected,b);b.peer=selected;observed=b.get();
 end
endmodule
module top;
 wire[7:0] a;wire[128:0] b;
 unit_test #(8) one(a);unit_test #(129) two(b);
 initial begin #2;$display("TRACE clones %h %h",a,b);$finish;end
endmodule
