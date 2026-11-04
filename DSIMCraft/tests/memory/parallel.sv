`timescale 1ns/1ps
module bank #(parameter SEED=3)(output reg [7:0] q);
  reg [7:0] mem [0:15];
  reg [4:0] i;
  wire [127:0] state={mem[15],mem[14],mem[13],mem[12],mem[11],mem[10],mem[9],mem[8],mem[7],mem[6],mem[5],mem[4],mem[3],mem[2],mem[1],mem[0]};
  initial begin
    i=0;
    repeat(16)begin mem[i]=i+SEED;i=i+1;end
    i=0;
    repeat(16)begin #1 q=mem[i];mem[i]<=#1 mem[i]+1;i=i+1;end
  end
endmodule
module top;
 wire [7:0] a,b;
 bank #(.SEED(3)) u(a);
 bank #(.SEED(17)) v(b);
endmodule
