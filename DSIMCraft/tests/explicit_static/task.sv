`timescale 1ns/1ps
module top;
integer a=0,b=0,q=0;
task automatic work(input integer n,output integer value);
 static integer calls=0;
 integer saved=n;
 calls++;
 #n;
 value=calls*10+saved;
 q+=saved;
endtask
initial begin
 fork
  work(2,a);
  begin #1;work(4,b);end
 join
 $display("TRACE task %0d %0d %0d",a,b,q);
 if(a!=22||b!=24||q!=6)$fatal(1,"shared static and private automatic");
end
endmodule
