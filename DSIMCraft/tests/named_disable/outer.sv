`timescale 1ns/1ps
module top;integer a=0,b=0;
initial begin
 begin : whole
  fork
   begin #2;disable whole;a=99;end
   begin #10;b=99;end
  join
  a=88;
 end
 a=1;#20;$display("TRACE outer %0d %0d %0t",a,b,$time);$finish;
end
endmodule
