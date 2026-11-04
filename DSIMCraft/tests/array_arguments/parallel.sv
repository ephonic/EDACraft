`timescale 1ns/1ps
module lane #(parameter PERIOD=1)(output integer total=0);
integer values[0:1];
function automatic integer add(ref integer a[2],input integer n);a[0]+=n;a[1]+=n;return a[0]+a[1];endfunction
task automatic modify(ref integer a[0:1]);#PERIOD;a[0]+=2;#PERIOD;a[1]+=3;endtask
initial begin values[0]=0;values[1]=0;total=add(values,1);modify(values);total=values[0]+values[1];end
endmodule
module top;wire signed[31:0]a,b;lane u(a);lane #(.PERIOD(2))v(b);endmodule
