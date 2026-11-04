`timescale 1ns/1ps
module top;
 string source,captured,copy;
 integer changes=0,length;reg done=0;
 always @(source) changes=changes+1;
 always @(source) length=source.len();
 initial begin #0.5;source="first";#1;source="second";#2;source="third";end
 initial begin
  #1;captured=#2 source;copy=captured;
  if(captured!="first"||source!="second"||length!=6) $fatal(1,"delayed snapshot");
  #1;
  if(copy!="first"||source!="third"||length!=5||changes!=3) $fatal(1,"copy or sensitivity");
  done=1;$display("TRACE timing [%s] [%s] %0d %0d",captured,source,length,changes);#0.25;$finish;
 end
endmodule
