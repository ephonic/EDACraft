`timescale 1ns/1ps
module top;
integer a=0,b=0,za=1,zb=2,flags=0,i;
task automatic work(input integer x,input integer hold,output integer y,inout integer z);
 integer saved=x+3,fresh;
 integer words[0:1];
 begin
  if(fresh!==32'bx||words[0]!==32'bx)flags=1;
  fresh=x;words[0]=x;
  #(hold);
  if(fresh!==x||words[0]!==x)flags=2;
  z+=saved;y=saved+x;
 end
endtask
initial begin work(2,5,a,za);if(a!==7||za!==6)$fatal(1,"long activation");$display("TRACE long %0t %0d %0d",$time,a,za);end
initial begin
 #1 work(7,2,b,zb);if(b!==17||zb!==12)$fatal(1,"short activation");
 $display("TRACE short %0t %0d %0d",$time,b,zb);
 #3;
 for(i=0;i<3;i=i+1)begin work(i,1,b,zb);if(b!==i*2+3)$fatal(1,"repeat task");end
 if(flags!==0||zb!==24)$fatal(1,"task local lifetime");
 $display("TRACE overlap complete");
end
endmodule
