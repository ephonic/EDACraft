"""Independent domains,mandatory merges and sparse-time compiled workloads."""
CASES={
 'independent': ('''`timescale 1ps/1ps
module top;reg [7:0] a,b;
initial begin a=0;repeat(3)begin #2 a=a+8'd1;end #5 $display("TRACE a=%b",a);$finish;end
initial begin b=0;repeat(2)begin #3 b=b+8'd2;end end
endmodule
''',2),
 'connected': ('''`timescale 1ps/1ps
module stage(input clk,input [7:0] a,output reg [7:0] q);
always @(posedge clk)q<=a;endmodule
module top;reg clk;reg [7:0] a;wire [7:0] q,r;
stage x(clk,a,q);stage y(clk,q,r);
initial begin clk=0;a=0;repeat(7)begin #2 clk=~clk;a=a+8'd1;end #3 $display("TRACE r=%b",r);$finish;end
endmodule
''',1),
 'hierarchy': ('''`timescale 1ps/1ps
module island #(parameter D=2);reg a;wire b,c;
assign #1 b=~a;not #1 (c,b);
initial begin a=0;repeat(4)begin #D a=~a;end end
endmodule
module top;island #(2) x();island #(3) y();initial begin #19 $finish;end endmodule
''',2),
 'wide-delays': ('''`timescale 1ps/1ps
module top;reg [1:0] a;reg [257:0] q;wire [257:0] z;reg [7:0] independent;
assign #3 z=q;
always @(a)q<=#2 {129{a}};
initial begin a=2'bxz;#2 a=2'b10;#3 a=2'bz1;#4 a=2'b01;end
initial begin independent=0;repeat(5)begin #2 independent=independent+8'd1;end end
initial begin #17 $finish;end
endmodule
''',2),
 'partial-multidriver': ('''`timescale 1ps/1ps
module pass(inout [3:0] b,input [3:0] a);assign b=a;endmodule
module top;reg [3:0] a,b;reg tick;wire [7:0] shared;
pass x(shared[7:4],a);pass y(shared[3:0],b);
assign shared[7:4]=b;
initial begin a=4'bzzzz;b=0;#2 a=5;#2 b=4'bxxxx;#2 b=4'bzzzz;end
initial begin tick=0;repeat(4)begin #3 tick=~tick;end end
initial begin #17 $finish;end
endmodule
''',2),
 'format-global': ('''`timescale 1ns/1ps
module top;reg a,b;
initial begin a=0;$timeformat(-9,2," ns",0);#1 a=1;$display("TRACE first %t",$time);end
initial begin b=0;#2 b=1;$display("TRACE second %t",$time);#1 $finish;end
endmodule
''',1),
 'sparse-quiescent': ('''`timescale 1ps/1ps
module top;reg a,b;
initial begin a=0;#64'd1125899906842624 a=1;end
initial begin b=0;#3 b=1;end
endmodule
''',2),
 'quiescent-output': ('''`timescale 1ps/1ps
module top;reg a,b;
initial begin a=0;$timeformat(-12,0," ps",0);#2 a=1;$display("TRACE a=%b t=%t",a,$time);end
initial begin b=0;#3 b=1;end
endmodule
''',2),
 'empty': ('module top;endmodule\n',1),
}
