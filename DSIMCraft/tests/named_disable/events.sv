`timescale 1ns/1ps
module top;event e;logic clk=0,allow=1;integer q=0,r=0,k=0;
initial begin
 for(k=0;k<3;k++)begin
  fork : round
   begin @(e iff allow);q=q+1;end
   begin @(posedge clk iff allow);r=r+1;end
   begin #2;disable round;end
  join
  ->e;clk=1;#0;clk=0;
 end
 #10;->e;clk=1;#1;$display("TRACE events %0d %0d %0d %0t",q,r,k,$time);
 if(q!==0||r!==0)$fatal(1,"cancelled wait woke up");
 $finish;
end
endmodule
