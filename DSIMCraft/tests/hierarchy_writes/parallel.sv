`timescale 1ps/1ps
module leaf;
  reg [15:0] word;
  reg [15:0] mem[0:1];
  wire [15:0] observed=word^mem[0];
endmodule
module top;
  leaf u(),v();
  initial begin u.word=0;u.mem[0]=0;u.mem[1]=0;#2;u.mem[0]=7;u.word=3;#2;u.word=9;end
  initial begin v.word=0;v.mem[0]=0;v.mem[1]=0;#1;v.mem[0]=11;v.word=5;#2;v.word=23;end
endmodule
