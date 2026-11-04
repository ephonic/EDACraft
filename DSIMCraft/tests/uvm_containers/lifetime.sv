`timescale 1ns/1ps
module top;
 int total=0;
 task automatic collect(input int seed);
   int q[$];int a[int];
   q.push_back(seed);a[-seed]=seed+1;
   #2;
   total+=q.pop_front()+a[-seed];
   $display("TRACE task %0d %0d %0d %0d",seed,q.size(),a.size(),a[-seed]);
 endtask
 function automatic int calc(input int seed);
   int q[$];int a[int];
   q.push_back(seed);a[-seed]=seed+2;
   return q.pop_back()+a[-seed];
 endfunction
 initial begin
  $display("TRACE functions %0d %0d",calc(2),calc(3));
  fork collect(3);begin #1;collect(5);end join
  $display("TRACE total %0d",total);
  collect(7);$display("TRACE again %0d",total);
 end
endmodule
