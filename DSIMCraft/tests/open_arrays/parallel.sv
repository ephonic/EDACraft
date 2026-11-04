`timescale 1ns/1ps
module lane #(parameter PERIOD=1)(output integer total=0);
integer words[2:1];
function automatic integer sum(input integer a[]);return a[0]+a[1];endfunction
task automatic change(inout integer a[]);#PERIOD;a[0]++;#PERIOD;a[1]+=2;endtask
initial begin words[2]=1;words[1]=2;total=sum(words);change(words);total=sum(words);end
endmodule
module top;wire signed[31:0] a,b;lane u(a);lane #(.PERIOD(2))v(b);endmodule
