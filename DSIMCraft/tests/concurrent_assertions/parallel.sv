`timescale 1ns/1ps
module lane(output integer result);
 reg clk=0,a=1,b=0;integer failures=0;
 always #5 clk=~clk;
 property p;@(posedge clk) a |=> b;endproperty
 aa: assert property(p) else failures=failures+1;
 initial begin #12;b=1;#10;b=0;#10;b=1;#10;result=failures;end
endmodule
module top;
 wire[31:0] one,two;lane x(one);lane y(two);
 initial begin #46;$finish;end
endmodule
