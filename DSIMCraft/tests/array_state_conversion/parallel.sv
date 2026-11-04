`timescale 1ns/1ps
module worker(output logic[15:0] q=0);
 logic[7:0] source[]=new[2];bit[7:0] copy[]=source;logic[7:0] back[]=copy;
 task automatic change(inout bit[7:0] x[]);x[0]++;x[1]++;#1;endtask
 initial begin
  #1;source[0]=8'b1xz001zx;source[1]=2;copy=source;back=copy;q={copy[0],back[1]};
  #1;change(back);q={back[0],back[1]};
 end
endmodule
module top;wire[15:0] one,two;worker u(one),v(two);endmodule
