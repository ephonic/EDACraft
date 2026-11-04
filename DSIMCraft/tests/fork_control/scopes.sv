`timescale 1ns/1ps
module top;integer a=0,b=0;
task automatic work(input integer n,output integer value);integer hold=n;#n;value=hold+10;endtask
initial begin fork work(2,a);work(4,b);join_any
$display("TRACE first %0d %0d %0t",a,b,$time);wait fork;
$display("TRACE scopes %0d %0d %0t",a,b,$time);#1;$finish;end endmodule
