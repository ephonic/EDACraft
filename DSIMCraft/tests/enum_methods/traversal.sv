`timescale 1ns/1ps
module top;
typedef enum logic signed [7:0] {LOW=-4,HIGH=9,MIDDLE=2} E;
typedef E Alias;
E e;Alias result;
integer i,n,total=0;
initial begin
e=LOW;
if(e.first()!==LOW||e.last()!==MIDDLE||e.num()!==3)$fatal(1,"bounds");
for(i=0;i<7;i++)begin
 result=e.next();total+=e;e=result;#1;
end
if(e!==HIGH||total!==10)$fatal(1,"order and wrap");
e=e.prev(2);if(e!==MIDDLE)$fatal(1,"reverse");
n=-1;result=e.next(n);if(result!==MIDDLE)$fatal(1,"unsigned count");
n=2;e=e.next(n);if(e!==HIGH)$fatal(1,"dynamic count");
if(e.next(0)!==HIGH||e.prev(0)!==HIGH)$fatal(1,"zero");
if(e.next(64'h100000001)!==MIDDLE||e.prev(64'h100000001)!==LOW)$fatal(1,"count truncation");
$display("TRACE traversal %0d %0d %0d",e,result,total);
end
endmodule
