`timescale 1ns/1ps
module top;
 integer source[2];integer count=0,done=0,k=0,observed=0;
 task automatic work(input integer tag);
  integer a[2]=source,b[2]=a;
  static integer shared[2]=source;
  a[0]+=tag;shared[0]++;#2;count+=a[0]+b[1];observed=shared[0];
 endtask
 initial begin
  source[0]=10;source[1]=2;
  for(k=1;k<=3;k++)begin
   begin:cancelled
    fork work(99);begin #1;disable cancelled;end join
   end
   work(k);done++;
  end
  $display("TRACE control %0d %0d %0d %0d",count,done,source[0],observed===32'bx);
 end
endmodule
