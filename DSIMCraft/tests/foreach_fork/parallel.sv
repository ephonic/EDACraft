`timescale 1ns/1ps
module lane #(parameter PERIOD=1)(output integer q=0);
logic [3:1] data=0;
integer n=0;
task work();
 foreach(data[i])begin #PERIOD;q+=i;end
endtask
initial begin
 for(n=0;n<4;n++)fork work();join_none
 wait fork;
end
endmodule
module top;
wire signed [31:0] a,b;
lane #(1)u(a);lane #(2)v(b);
endmodule
