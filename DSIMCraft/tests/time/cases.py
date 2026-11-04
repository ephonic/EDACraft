"""Timing cases use race-free TRACE output, checked independently against VCS."""
CASES={
'mixed':('''`timescale 10ns/1ns
module child;
 initial begin #0.15;$display("TRACE child1 d=%0d t=%0t",$time,$time);#0.05;$display("TRACE child2 d=%0d t=%0t",$time,$time);end
endmodule
`timescale 1ns/1ps
module top;
 child c();
 initial begin
 #1.25;$display("TRACE top1 d=%0d t=%0t",$time,$time);
 #0.25;$display("TRACE top2 d=%0d t=%0t",$time,$time);
 #2;$finish;end
endmodule
''',['TRACE top1 d=1 t=1000','TRACE top2 d=2 t=2000','TRACE child1 d=0 t=0','TRACE child2 d=0 t=0']),
'fractions':('''`timescale 1ns/100ps
module top;
 reg a;
 initial begin a=0;
 #0.149;a=1;$display("TRACE a d=%0d t=%0t",$time,$time);
 #0.05;a=0;$display("TRACE b d=%0d t=%0t",$time,$time);
 #1.25e0;a=1;$display("TRACE c d=%0d t=%0t",$time,$time);
 #1_0e-1;a=0;$display("TRACE d d=%0d t=%0t",$time,$time);
 #0.01;$display("TRACE e d=%0d t=%0t",$time,$time);$finish;
 end endmodule
''',['TRACE a d=0 t=0','TRACE b d=0 t=0','TRACE c d=2 t=20','TRACE d d=3 t=30','TRACE e d=3 t=30']),
'format':('''`timescale 10ns/1ns
module top;
 initial begin
 #0.15;$display("TRACE d=%0d t=%0t literal=%0t default=[%t]",$time,$time,12,0);
 $timeformat(-9,2," ns",12);
 $display("TRACE a=[%t] b=[%0t] c=[%2t] z=[%0t] x=[%0t] mix=[%0t]",12,12,12,8'bz,8'bx,8'bx01);
 $timeformat(-7,0,"",2);$display("TRACE r=%0t,%0t,%0t",4,5,6);
 $finish;end endmodule
''',['TRACE d=0 t=0 literal=120 default=[                   0]','TRACE a=[   120.00 ns] b=[120.00 ns] c=[120.00 ns] z=[0] x=[0] mix=[0]','TRACE r=0,0,1']),
'parameter':('''`timescale 100ps/10ps
module child #(parameter N=2) (output reg q);
 initial begin q=0;#N;q=1;$display("TRACE child d=%0d t=%0t",$time,$time);end
endmodule
`timescale 1ns/1ps
module top;
 wire a,b;child u(a);child #(3) v(b);
 initial begin #1;$display("TRACE top d=%0d t=%0t a=%b b=%b",$time,$time,a,b);$finish;end
endmodule
''',['TRACE child d=2 t=200','TRACE child d=3 t=300','TRACE top d=1 t=1000 a=1 b=1']),
'unused':('''`timescale 1ns/1ns
module top;initial begin #1;$display("TRACE unused=%0t",$time);$finish;end endmodule
`timescale 1fs/1fs
module unused;endmodule
''',['TRACE unused=1000000']),
'default':('''module top;initial begin #1;$display("TRACE default d=%0d t=%0t",$time,$time);$finish;end endmodule
''',['TRACE default d=1 t=1']),
'resetall':('''`define KEEP 2
`timescale 1ps/1ps
module child;initial begin #1;$display("TRACE child=%0t",$time);end endmodule
`resetall
module top;
 child c();
 initial begin #`KEEP;$display("TRACE reset d=%0d t=%0t",$time,$time);$finish;end
endmodule
''',['TRACE child=1','TRACE reset d=2 t=2000000000000']),
}
# A visible bit also lets both waveform readers validate physical timestamps.
CASES={name:(source.replace('module top;','module top;reg tick;initial tick=0;'),expected) for name,(source,expected) in CASES.items()}
