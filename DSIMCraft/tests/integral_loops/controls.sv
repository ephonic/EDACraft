`timescale 1ns/1ps
module top;
 integer i=0,q=0;
 initial begin
  for(i=0;i<8;i++)begin #1;if(i==2)continue;if(i==6)break;q=q+i;end
  $display("TRACE controls %0d %0d %0t",i,q,$time);
  do begin q=q-1;end while(q>10);
  repeat(3)q=q+2;
  $display("TRACE repeat %0d",q);$finish;
 end
endmodule
