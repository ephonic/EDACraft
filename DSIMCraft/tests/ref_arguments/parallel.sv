`timescale 1ns/1ps
module lane #(parameter PERIOD=1)(output integer total=0);
function automatic integer add(ref integer a,input integer n);a+=n;return a;endfunction
task automatic modify(ref integer a);#PERIOD;a+=2;#PERIOD;a+=3;endtask
initial begin total=add(total,1);modify(total);end
endmodule
module top;wire signed[31:0] a,b;lane u(a);lane #(.PERIOD(2))v(b);endmodule
