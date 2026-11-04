"""Race-free RTL delayed NBA traces, independently checked with VCS."""
CASES = {
    'regions': ('''`timescale 1ns/1ps
module top;
 reg [7:0] source=8'h11,q=0;
 initial begin
  q <= #5 source; source=8'h22; q <= #5 source; source=8'h33;
  $display("TRACE immediate t=%0t q=%h",$time,q);
  #5; $display("TRACE active t=%0t q=%h",$time,q);
  #0; $display("TRACE inactive t=%0t q=%h",$time,q);
  #0.001; $display("TRACE committed t=%0t q=%h",$time,q); $finish;
 end
endmodule
''', ['TRACE immediate t=0 q=00','TRACE active t=5000 q=00',
      'TRACE inactive t=5000 q=00','TRACE committed t=5000 q=22']),
    'zero': ('''`timescale 1ns/1ps
module top;
 reg [7:0] source=8'h12,q=0;
 initial begin
  q <= #0 source; source=8'h34;
  $display("TRACE active q=%h",q);
  #0; $display("TRACE inactive q=%h",q);
  #0.001; $display("TRACE committed q=%h",q); $finish;
 end
endmodule
''', ['TRACE active q=00','TRACE inactive q=00','TRACE committed q=12']),
    'transport': ('''`timescale 1ns/1ps
module top;
 reg [7:0] source=0,q=0;
 initial begin
  source=1; q <= #5 source;
  #1; source=2; q <= #5 source;
  #1; source=3; q <= #5 source;
  #3.001; $display("TRACE first q=%h",q);
  #1; $display("TRACE second q=%h",q);
  #1; $display("TRACE third q=%h",q); $finish;
 end
endmodule
''', ['TRACE first q=01','TRACE second q=02','TRACE third q=03']),
    'parts': ('''`timescale 1ns/1ps
module top;
 reg [7:0] q=8'hf0;reg a=0;reg [3:0] hi=0,lo=0;
 initial begin
  q[7:4] <= #2 4'h3; {hi,lo} <= #2 8'hxz;
  {a,a} <= #2 2'b10; #1; q[3:0]=4'ha;
  #1.001; $display("TRACE parts q=%h hi=%h lo=%h a=%b",q,hi,lo,a); $finish;
 end
endmodule
''', ['TRACE parts q=3a hi=x lo=z a=0']),
    'wide': ('''`timescale 1ns/1ps
module top;
 reg [256:0] source={1'b1,256'h123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0};
 reg [256:0] q=0;
 initial begin
  q <= #3 source; source=0;
  #3.001; $display("TRACE wide q=%h",q);
  q[256:128] <= #1 129'h1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx;
  #1.001; $display("TRACE mixed q=%h",q); $finish;
 end
endmodule
''', ['TRACE wide q=1123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0',
      'TRACE mixed q=1'+'x'*32+'123456789abcdef0123456789abcdef0']),
    'precision': ('''`timescale 10ns/1ns
module coarse(output reg [7:0] q);
 parameter D=1;
 reg [7:0] source=8'h11;
 initial begin q <= #0.15 source;source=8'h22;q <= #(D) source;source=8'h33;end
endmodule
`timescale 1ns/1ps
module top;
 wire [7:0] q;coarse c(q);
 initial begin
  #1.999; $display("TRACE before q=%h",q);
  #0.002; $display("TRACE rounded q=%h",q);
  #8; $display("TRACE parameter q=%h",q); $finish;
 end
endmodule
''', ['TRACE before q=xx','TRACE rounded q=11','TRACE parameter q=22']),
    'loop': ('''`timescale 1ns/1ps
module top;
 parameter D=3;
 reg [7:0] source=0,q=0;
 initial begin
  repeat(4) begin source=source+1; q <= #D ((source==2)?8'hxz:source); #1; end
  #0.001;$display("TRACE second q=%h",q);
  #1;$display("TRACE third q=%h",q);
  #1;$display("TRACE fourth q=%h",q);$finish;
 end
endmodule
''', ['TRACE second q=xz','TRACE third q=03','TRACE fourth q=04']),
    'clock': ('''`timescale 1ns/1ps
module top;
 reg clk=0;reg [7:0] source=8'h11,q=0;
 always #1 clk=~clk;
 always @(posedge clk) q <= #0.5 source;
 initial begin
  #1.25;source=8'h22;#0.5;$display("TRACE clock1 q=%h",q);
  #1.5;source=8'h33;#0.5;$display("TRACE clock2 q=%h",q);
  #1.5;source=8'h44;#0.5;$display("TRACE clock3 q=%h",q);$finish;
 end
endmodule
''', ['TRACE clock1 q=11','TRACE clock2 q=22','TRACE clock3 q=33']),
    'finish': ('''`timescale 1ns/1ps
module top;
 reg [7:0] q=0;
 initial begin q <= #100 8'hff; #1; $display("TRACE finish q=%h",q);$finish;end
endmodule
''', ['TRACE finish q=00']),
}
