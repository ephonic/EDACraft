`timescale 1ns/1ps
module top;
event a,b,c;
integer left=0,right=0,total=0;
task automatic watch(input integer n,output integer result);
 integer saved=n;
 wait_order(a,b,c) result=saved;else result=-saved;
 total+=result;
endtask
initial begin
 fork
  watch(3,left);
  watch(7,right);
  begin #1;->a;#1;->b;#1;->c;end
 join
 $display("TRACE tasks %0d %0d %0d",left,right,total);
 if(left!=3||right!=7||total!=10)$fatal(1,"automatic ordered task");
end
endmodule
