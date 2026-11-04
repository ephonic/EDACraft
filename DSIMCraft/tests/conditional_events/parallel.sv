`timescale 1ns/1ps
module lane #(parameter PERIOD=1)(output integer total=0);
logic clk=0,enable=0;integer k=0;
task automatic watch(input integer amount);
logic local_enable=1;
begin @(posedge clk iff (enable && local_enable));total+=amount;end
endtask
initial begin #0;watch(1);watch(2);end
initial #PERIOD enable=1;
initial begin
#PERIOD;
for(k=0;k<4;k++)begin #PERIOD clk=1;#PERIOD clk=0;end
end
endmodule
module top;wire[31:0]a,b;lane #(.PERIOD(1))u(a);lane #(.PERIOD(2))v(b);endmodule
