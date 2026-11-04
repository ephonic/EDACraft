`timescale 1ns/1ps
module top;
integer q=0,seq=0,error=0,i;
function integer next();begin seq++;return seq;end endfunction
task automatic blocks(input integer count,output integer result);
 integer sum=0,j;
 begin
  for(j=0;j<count;j=j+1)begin:iteration
   integer stamp=next(),sample=j+2,fresh;
   bit zero;
   if(fresh!==32'bx||zero!==0)error=1;
   fresh=99;zero=1;
   #1 sum+=sample+stamp;
  end
  result=sum;
 end
endtask
initial begin
 blocks(3,q);if(q!==15||seq!==3||error!==0)$fatal(1,"nested block entry");
 blocks(2,q);if(q!==14||seq!==5||error!==0)$fatal(1,"new task initialization");
 for(i=0;i<2;i=i+1)begin blocks(1,q);if(q!==i+8||seq!==i+6)$fatal(1,"same callsite");end
 $display("TRACE blocks complete");
end
endmodule
