`timescale 1ns/1ps
module lane #(parameter ID=0)(output integer fails);
 reg clk=0,q=ID;
 initial fails=0;
 always #5 clk=~clk;
 a: assert property(p) else fails=fails+1;
 property p;@(posedge clk) q |=> q;endproperty
 initial begin #12;q=~q;#10;q=~q;end
endmodule
module top;
 wire [31:0] one,two;
 lane #(0) x(one);lane #(1) y(two);
 initial begin #46;$display("TRACE clones %0d %0d",one,two);$finish;end
endmodule
