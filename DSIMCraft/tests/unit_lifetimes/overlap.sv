`timescale 1ns/1ps
interface automatic work_if #(parameter BIAS=3);
 integer errors=0,completed=0;
 task work(input integer x,input integer hold,output integer y,ref integer z);
  integer saved=x+BIAS,fresh;integer words[0:1];
  begin
   if(fresh!==32'bx||words[0]!==32'bx)errors++;
   fresh=x;words[0]=x;#(hold);
   if(fresh!==x||words[0]!==x)errors++;
   z+=saved;y=saved+x;completed++;
  end
 endtask
 function integer inc(ref integer x);integer saved=1;x+=saved;return x;endfunction
 modport worker(import task work(input integer x,input integer hold,output integer y,ref integer z),import function integer inc(ref integer x));
endinterface
module automatic client(work_if.worker bus,output integer a,output integer b);
 integer za=1,zb=2,ra;
 initial begin bus.work(2,5,a,za);if(a!=7||za!=6)$fatal(1,"long activation");$display("TRACE long %0t %0d %0d",$time,a,za);end
 initial begin #1;bus.work(7,2,b,zb);if(b!=17||zb!=12)$fatal(1,"short activation");$display("TRACE short %0t %0d %0d",$time,b,zb);
 #3;ra=bus.inc(za);if(ra!=7||za!=7)$fatal(1,"inherited ref function");end
endmodule
module top;
 work_if #(.BIAS(3)) w();integer a,b;client c(w,a,b);
 initial begin #7;if(w.errors!=0||w.completed!=2)$fatal(1,"interface overlap");$display("TRACE overlap %0d %0d",w.errors,w.completed);end
endmodule
