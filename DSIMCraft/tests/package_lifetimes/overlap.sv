`timescale 1ns/1ps
package automatic work_pkg;
 integer errors=0,completed=0;
 task work(input integer x,input integer hold,output integer y,inout integer z);
  integer saved=x+3,fresh;
  integer words[0:1];
  begin
   if(fresh!==32'bx||words[0]!==32'bx)errors++;
   fresh=x;words[0]=x;#(hold);
   if(fresh!==x||words[0]!==x)errors++;
   z+=saved;y=saved+x;completed++;
  end
 endtask
endpackage
module top;
 integer a=0,b=0,za=1,zb=2;
 initial begin work_pkg::work(2,5,a,za);if(a!=7||za!=6)$fatal(1,"long activation");$display("TRACE long %0t %0d %0d",$time,a,za);end
 initial begin #1;work_pkg::work(7,2,b,zb);if(b!=17||zb!=12)$fatal(1,"short activation");$display("TRACE short %0t %0d %0d",$time,b,zb);
 #3;if(work_pkg::errors!=0||work_pkg::completed!=2)$fatal(1,"package task overlap");$display("TRACE overlap %0d %0d",work_pkg::errors,work_pkg::completed);end
endmodule
