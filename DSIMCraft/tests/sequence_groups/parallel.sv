`timescale 1ns/1ps
module lane #(parameter D=1)(output integer result=0);
  reg clk=0,a=1,b=1;integer failed=0;
  always #5 clk=~clk;
  property p;@(negedge clk) a |-> ##D (b ##0 a)[*(D+1)];endproperty
  ap:assert property(p) result++;else failed++;
  initial begin #23;b=0;#10;b=1;#30;a=0;end
endmodule
module top;
  wire [31:0] one,two;lane #(1) x(one);lane #(2) y(two);
  initial begin #102;$finish;end
endmodule
