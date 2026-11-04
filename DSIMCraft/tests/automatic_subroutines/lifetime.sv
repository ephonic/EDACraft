`timescale 1ns/1ps
module top;
integer seq=0,q=0,out=0,total=0,i;
function integer next();begin seq++;return seq;end endfunction
function automatic integer calculate(input integer x,output integer y);
 integer a=x+1,b=a+1,stamp=next(),fresh;
 bit clean;
 logic[129:0] scratch;
 integer words[2:3];
 begin
  if(fresh!==32'bx||clean!==0||scratch!==130'bx||words[2]!==32'bx)return -999;
  a++;words[2]=x;fresh=77;clean=1;scratch=0;
  if(x==1)y=7;
  return a+b+stamp;
 end
endfunction
function automatic integer maybe(input integer x);
 begin if(x) return 8;return;end
endfunction
initial begin
 q=calculate(1,out);if(q!==7||out!==7||seq!==1)$fatal(1,"first frame");
 q=calculate(2,out);if(q!==10||out!==32'bx||seq!==2)$fatal(1,"new call frame");
 for(i=0;i<3;i=i+1)begin
  q=calculate(1,out);total+=q;
  if(out!==7)$fatal(1,"output reset");
 end
 if(total!==30||seq!==5)$fatal(1,"repeated frame initializer");
 q=maybe(1);if(q!==8)$fatal(1,"return assigned");
 q=maybe(0);if(q!==32'bx)$fatal(1,"return reset");
 #1 $display("TRACE lifetime %0d %0d",seq,total);
end
endmodule
