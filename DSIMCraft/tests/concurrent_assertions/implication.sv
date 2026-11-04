`timescale 1ns/1ps
module top;
 reg clk=0,a=0,b=0;integer passed=0,failed=0,covered=0,overlap=0;
 always #5 clk=~clk;
 property p;@(posedge clk) a |=> b;endproperty
 n: assert property(p) passed=passed+1;else failed=failed+1;
 o: assert property(@(posedge clk) a |-> b) else overlap=overlap+1;
 c: cover property(@(posedge clk) a |=> b) covered=covered+1;
 initial begin
  #2;a=1;b=0;#10;a=0;b=1;#10;a=1;b=0;#10;b=1;#10;a=0;b=0;
  #10;$display("TRACE implication %0d %0d %0d %0d",passed,failed,covered,overlap);$finish;
 end
endmodule
