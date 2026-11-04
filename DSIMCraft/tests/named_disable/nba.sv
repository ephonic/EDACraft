`timescale 1ns/1ps
module top;event e;integer a=0,b=0,c=0;
initial begin
 fork : jobs
  begin a<=#5 11;b<=@e 22;#20;c=99;end
  begin #2;disable jobs;end
 join
 $display("TRACE joined %0d %0d %0d %0t",a,b,c,$time);
 #1;->e;#3;$display("TRACE retained %0d %0d %0d %0t",a,b,c,$time);$finish;
end
endmodule
