`timescale 1ns/1ps
module top;
 logic[7:0] source[3:2];integer observed=0,calls=0;
 task automatic work(const ref logic[7:0] input_values[2],input integer n);
  bit[7:0] a[2]=input_values,b[1:0]=a;
  logic[7:0] c[2]=b;
  a[0]+=n;#1;observed=a[0]+c[0];calls++;
  $display("TRACE local %0d %h %h %h %0d",n,a[0],b[1],c[1],observed);
 endtask
 function automatic integer sum(input logic[7:0] x[2]);
  bit[7:0] a[2]=x,b[2]=a;
  a=b;return a[0]+b[1];
 endfunction
 initial begin
  source[3]=8'b1xz001zx;source[2]=8'hcd;
  work(source,1);work(source,2);observed=sum(source);
  $display("TRACE function %0d %0d %0d",observed,calls,source[3]===8'b1xz001zx);
 end
endmodule
