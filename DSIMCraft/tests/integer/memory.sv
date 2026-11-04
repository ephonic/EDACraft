`timescale 1ns/1ps
module top;
integer mem[5:2], idx, saved;
reg signed [63:0] extended;
reg [127:0] all_words;
initial begin : worker
  integer temp;
  integer localmem[1:0];
  reg [63:0] localview;
  for(idx=2;idx<=5;idx=idx+1)mem[idx]=-idx;
  idx=3; localmem[0]=mem[idx]; localmem[1]=-12;
  temp=localmem[0];localview={localmem[1],localmem[0]};
  mem[idx] <= #2 temp-7;
  idx=4; mem[idx]=#1 -99;
  #2;
  saved=mem[3]; extended=mem[5];
  all_words={mem[5],mem[4],mem[3],mem[2]};
  $display("TRACE memory %0d %0d %h %h %h",temp,saved,extended,all_words,localview);
  mem[2][7:0]=8'h80;
  #1 $display("TRACE select %h",mem[2]);
  idx=-1; saved=mem[idx];
  #1 $display("TRACE invalid %h",saved);
  $finish;
end
endmodule
