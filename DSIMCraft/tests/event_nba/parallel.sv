`timescale 1ns/1ps
module lane #(parameter PERIOD=1)(output integer total=0);
event e;logic enable=0;integer k=0;
function automatic logic gate(input logic x);return x&&enable;endfunction
task automatic issue(input integer amount,input integer count);total<=repeat(count)@(e iff gate(enable))amount;endtask
initial begin #0;issue(1,1);issue(3,3);end
initial #PERIOD enable=1;
initial begin #PERIOD;for(k=0;k<4;k++)begin #PERIOD;->e;end end
endmodule
module top;wire[31:0]a,b;lane #(.PERIOD(1))u(a);lane #(.PERIOD(2))v(b);endmodule
