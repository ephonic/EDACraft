`timescale 1ns/1ps
module top;
event e;logic clk=0,allow=0;integer q=0,r=0;
initial begin
 fork
  begin @(posedge clk iff allow);q=11;end
  begin repeat(2)@e;r=22;end
  begin #1;clk=1;#1;allow=1;clk=0;#1;clk=1;#1;->e;#1;->e;end
 join
 $display("TRACE events %0d %0d %0t",q,r,$time);
 fork
  q<=@e 33;
  begin #1;->e;end
 join
 $display("TRACE pending %0d %0d %0t",q,r,$time);
 #1;$display("TRACE delivered %0d %0d %0t",q,r,$time);
 if(q!==33||r!==22)$fatal(1,"event join mismatch");
 $finish;
end
endmodule
