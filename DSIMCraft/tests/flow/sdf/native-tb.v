`timescale 1ps/1ps
module top;reg a;wire x,y;dut d(a,x,y);
`ifdef VCS_REFERENCE
initial begin $sdf_annotate("delay.sdf",d,,"annotation.log","TYPICAL");$dumpfile("vcs.vcd");$dumpvars(0,top);end
`endif
always @(x or y) $display("TRACE t=%0t x=%b y=%b",$time,x,y);
initial begin a=0;#100;a=1;#100;a=1'bz;#100;a=1'bx;#100;a=0;#100;a=1'bx;#100;a=1;#100;a=1'bx;#100;a=1'bz;#100;a=0;#100;a=1'bz;#100;a=1;#100;a=0;#100;#100;$finish;end endmodule
