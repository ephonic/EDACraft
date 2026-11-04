`timescale 1ps/1ps
module unit_test #(parameter W=8)(output logic [W-1:0] observed);
 class Base;
  logic [W-1:0] bits;
  function new();bits='1;endfunction
  virtual function [W-1:0] get();return bits;endfunction
 endclass
 class Derived extends Base;
  function [W-1:0] get();return bits ^ W'(3);endfunction
 endclass
 Derived d;Base b;
 initial begin d=new;b=d;#1;observed=b.get();#1;$display("TRACE clone W=%0d bits=%h",W,observed);end
endmodule
module top;
 wire [7:0] a;wire [128:0] b;
 unit_test #(8) u(a);unit_test #(129) v(b);
 initial begin #3;$finish;end
endmodule
