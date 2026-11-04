`timescale 1ns/1ps
module top;
logic [63:0] bus=0;
logic enable=0, other=0;
integer positive=0,negative=0,anyedge=0,delayed=0,alternate=0;
logic [63:0] combined;
always_comb combined=bus ^ {64{enable}};
always @(posedge bus or negedge bus) anyedge++;
always @(posedge bus) positive++;
always @(negedge bus) negative++;
// The extra delay requires the ordinary subscription path for this signal.
always begin @(other); #1; delayed++; end
// Multiple sites on the same process cannot use a fixed subscription.
always begin @(posedge enable); alternate++; @(negedge other); alternate++; end
initial begin
 #2; positive=0;negative=0;anyedge=0;delayed=0;
 #2; bus=64'h8000000000000000; other=1;
 #2; enable=1; bus=1;
 #2; bus=64'hxxxxxxxxxxxxxxxx; other=0;
 #2; bus=64'hzzzzzzzzzzzzzzzz;
 #2; bus=0; enable=0;
 #2; bus=1;
 #2; bus=0;
 #2;
 if(positive!==2||negative!==3||anyedge!==5||delayed!==2||alternate!==2||combined!==0)
   $fatal(1,"notification controls %0d %0d %0d %0d %0d %h",positive,negative,anyedge,delayed,alternate,combined);
 $display("TRACE notifications %0d %0d %0d %0d %0d %h",positive,negative,anyedge,delayed,alternate,combined);
 $finish;
end
endmodule
