`timescale 1ns/1ps
module lane #(parameter PERIOD=1)(output integer total=0);
event a,b,c;
initial begin wait_order(a,b,c) total=6;else total=-1;end
initial begin #PERIOD;->a;#PERIOD;->b;#PERIOD;->c;end
endmodule
module top;
wire signed[31:0] a,b;
lane u(a);lane #(.PERIOD(2))v(b);
endmodule
