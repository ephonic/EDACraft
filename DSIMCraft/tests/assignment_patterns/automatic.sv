`timescale 1ns/1ps
module top;
 typedef struct packed {bit[3:0] tag;logic[7:0] data;} item_t;
 integer observed=0;
 task automatic work(input integer k);
  integer a[2]='{k,k+1};
  item_t s='{tag:4'hf,data:8'h80};
  a='{a[1]+1,a[0]+2};s='{tag:k,data:a[0]};
  #1;observed=a[0]+a[1]+s.data;
  $display("TRACE task %0d %0d %0d %h %0d",k,a[0],a[1],s,observed);
 endtask
 function automatic integer sum(input integer k);
  integer a[2]='{k,k+1};
  a='{a[1],a[0]};sum=a[0]+a[1];
 endfunction
 initial begin
  work(3);work(8);observed=sum(5);
  $display("TRACE function %0d",observed);
 end
endmodule
