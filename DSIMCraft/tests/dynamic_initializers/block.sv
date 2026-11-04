`timescale 1ns/1ps
module top;
integer n=2;
task automatic work(input integer tag);static integer values[]=new[n];integer fresh[]=new[tag];
$display("TRACE block %0d %0d %0d %h",tag,values.size(),fresh.size(),values[0]);values[0]=tag;endtask
initial begin
n=7;work(2);work(3);
repeat(2)begin : b automatic integer a[]=new[n];$display("TRACE nested %0d",a.size());n++;end
end endmodule
