`timescale 1ns/1ps
module lane #(parameter PERIOD=1)(output integer total=0);
integer source=1;
function automatic integer inspect(const ref integer a);return a;endfunction
task automatic observe(const ref integer a);#(PERIOD+1);total=inspect(a);#PERIOD;total=inspect(a);endtask
initial fork observe(source);begin #PERIOD;source<=3;#PERIOD;source<=6;end join
endmodule
module top;wire signed[31:0] a,b;lane u(a);lane #(.PERIOD(2))v(b);endmodule
