`timescale 1ns/1ps
module top;integer a=0,b=0;
always begin
 fork
  begin #1;a=a+1;end
  begin #2;b=b+2;end
 join
 #1;
end
initial begin
 #9;$display("TRACE always %0d %0d %0t",a,b,$time);
 if(a!==3||b!==6)$fatal(1,"always join mismatch");
 $finish;
end
endmodule
