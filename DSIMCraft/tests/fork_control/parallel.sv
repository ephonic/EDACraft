`timescale 1ns/1ps
module lane #(parameter PERIOD=1)(output integer total=0);integer k=0,bad=0;
initial begin for(k=0;k<3;k++)begin
fork begin #PERIOD;total=total+1;end begin #(10*PERIOD);bad=bad+1;end join_any
disable fork;wait fork;end end endmodule
module top;wire[31:0]a,b;lane #(.PERIOD(1))u(a);lane #(.PERIOD(2))v(b);endmodule
