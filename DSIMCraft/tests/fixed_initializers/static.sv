`timescale 1ns/1ps
module top;
 integer source[3:2];integer early[2]=source;integer calls=0;
 function automatic integer fill();source[3]=7;source[2]=9;calls++;return 0;endfunction
 integer seed[]=new[fill()];integer later[1:0]=source,independent[2]=later;
 bit[7:0] zeros[2];logic[7:0] known[2]=zeros;bit[7:0] converted[2]=known;
 integer observed=0;
 initial begin
  $display("TRACE startup %h %h %0d %0d %0d",early[0],early[1],later[1],later[0],calls);
  source[3]=99;later[1]=11;observed=independent[0]+independent[1];
  $display("TRACE independent %0d %0d %h %h",independent[0],independent[1],known[0],converted[1]);
  #1;observed++;
 end
endmodule
