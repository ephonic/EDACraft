`timescale 1ns/1ps
module lane #(parameter D=1)(output integer result=0);
reg clk=0,a=1,b=1;integer failed=0;
always #5 clk=~clk;
property p;@(negedge clk) a |-> ##(D+1) b ##D a;endproperty
ap:assert property(p) result=result+1;else failed=failed+1;
initial begin #23;b=0;#10;b=1;#30;a=0;end
endmodule
module top;
wire[31:0] one,two;lane #(.D(1)) x(one);lane #(.D(2)) y(two);
initial begin #102;$finish;end
endmodule
