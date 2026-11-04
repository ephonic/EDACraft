`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 int n;integer j;logic[31:0]v;logic[63:0]v64;logic[32:0]v33;logic[15:0]v16;logic[129:0]w;int r;
 initial begin
 r=$value$plusargs("n=%d",n);r=$value$plusargs("n=%d",j);r=$value$plusargs("n=%d",v);r=$value$plusargs("n=%d",v16);r=$value$plusargs("n=%d",v33);r=$value$plusargs("n=%d",v64);r=$value$plusargs("n=%d",w);
 $display("TRACE TYPES %h %h %h %h %h %h %h",n,j,v,v16,v33,v64,w);
 r=$value$plusargs("h=%h",n);r=$value$plusargs("h=%h",v16);r=$value$plusargs("h=%h",v33);r=$value$plusargs("h=%h",w);
 $display("TRACE HEX %h %h %h %h",n,v16,v33,w);#1;$finish;
 end
endmodule
