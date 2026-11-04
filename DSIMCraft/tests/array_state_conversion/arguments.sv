`timescale 1ns/1ps
module top;
 logic[7:0] a[]=new[2];bit[7:0] result[];integer observed=0;
 function automatic integer sum(input bit[7:0] x[]);return x[0]+x[1];endfunction
 task automatic grow(inout bit[7:0] x[]);
  x[0]++;x=new[3](x);x[2]=8'haa;#1;
 endtask
 task automatic produce(output logic[7:0] x[]);
  x=new[2];x[0]=8'b1xz001zx;x[1]=8'hff;
 endtask
 initial begin
  a[0]=8'b1xz001zx;a[1]=2;observed=sum(a);
  $display("TRACE input %0d %0d",observed,a[0]===8'b1xz001zx);
  grow(a);$display("TRACE inout %0d %h %h %h",a.size(),a[0],a[1],a[2]);
  produce(result);observed=result[0]+result[1];
  $display("TRACE output %0d %h %h",result.size(),result[0],result[1]);
 end
endmodule
