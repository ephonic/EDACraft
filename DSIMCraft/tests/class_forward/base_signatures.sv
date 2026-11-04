`timescale 1ps/1ps
module top;
 typedef class Base;
 class Derived extends Base;
  function Derived self();return this;endfunction
 endclass
 class Base;
  function Derived pass(Derived value);return value;endfunction
 endclass
 Derived d=new;int observed;
 initial begin
  observed=d.pass(d.self())==d;
  #1;$display("TRACE base signatures %0d",observed);
 end
endmodule
