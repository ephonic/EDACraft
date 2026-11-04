`timescale 1ns/1ps
module lane #(parameter PERIOD=1)(output integer total=0);
event e;logic enable=0;integer k=0;
function automatic logic gate(input logic x);return x&&enable;endfunction
task automatic watch(input integer amount,input integer count);logic local_enable=1;logic[129:0]value;
begin value=repeat(count)@(e iff gate(local_enable))amount;total+=value;end endtask
initial begin #0;watch(1,1);watch(2,2);end
initial #PERIOD enable=1;
initial begin #PERIOD;for(k=0;k<4;k++)begin #PERIOD;->e;end end
endmodule
module top;wire[31:0]a,b;lane #(.PERIOD(1))u(a);lane #(.PERIOD(2))v(b);endmodule
