`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 int a[4],i=0,r;logic[129:0] wide;
 initial begin
 r=$value$plusargs("missing=%d",a[i++]);$display("TRACE MISS %0d %0d %0d",r,i,a[0]);
 r=$value$plusargs("n=%d",a[i++]);$display("TRACE HIT %0d %0d %0d %0d %0d",r,i,a[0],a[1],a[2]);
 r=$value$plusargs("h=%h",wide);$display("TRACE WIDE %0d %h",r,wide);
 r=$value$plusargs("bad=%d",a[0]);$display("TRACE BAD %0d %h",r,a[0]);
 r=$value$plusargs("o=%o",wide);$display("TRACE OCT %0d %h",r,wide);
 #2;$finish;
 end
endmodule
