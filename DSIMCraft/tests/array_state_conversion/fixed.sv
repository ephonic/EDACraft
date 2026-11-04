`timescale 1ns/1ps
module top;
 logic[7:0] source[3:2],words[2][2];bit[7:0] result[2];bit[7:0] copy[];
 integer observed=0,index=1;
 task automatic change(inout bit[7:0] x[2]);x[0]++;x[1]=8'haa;#1;endtask
 task automatic change_open(inout bit[7:0] x[]);x[0]+=2;x[1]=8'hbb;endtask
 task automatic produce(output logic[7:0] x[2]);x[0]=8'b1xz001zx;x[1]=8'hff;endtask
 function automatic integer sum(input logic[7:0] x[2]);return x[0]+x[1];endfunction
 initial begin
  source[3]=8'b1xz001zx;source[2]=8'hcd;copy=source;
  change(source);$display("TRACE fixed %h %h %h",source[3],source[2],copy[0]);
  words[0][0]=1;words[0][1]=2;words[1][0]=8'b1xz001zx;words[1][1]=3;
  change_open(words[index]);produce(result);observed=sum(result);
  $display("TRACE open %h %h %0d %h %h",words[1][0],words[1][1],observed,result[0],result[1]);
 end
endmodule
