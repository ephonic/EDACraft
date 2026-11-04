`timescale 1ns/1ps
module top;
integer seq=0,base=7,target=0,io=10,q=0;
function integer next();begin seq++;return seq;end endfunction
function integer f(input integer a=next(),input integer b=next(),output integer c=target,inout integer d=io);
 begin c=a*10+b;d+=c;return c;end
endfunction
function integer identity(input integer x=8);begin return x;end endfunction
function integer classic;input integer a;input integer b;begin return a+b;end endfunction
initial begin
 q=f(.b(next()),.a(next()));
 $display("TRACE named %0d %0d %0d %0d",q,seq,target,io);
 q=f(,9);$display("TRACE empty %0d %0d %0d %0d",q,seq,target,io);
 begin:local_scope
  integer base=100,target=200,io=300;
  q=f(.a(base));
  $display("TRACE lexical %0d %0d %0d %0d",q,seq,target,io);
 end
 $display("TRACE outer %0d %0d",target,io);
 #1 q=f(,5,.d(io));if(q!==55||seq!==5||target!==55||io!==1120)$fatal(1,"mixed binding");
 q=f(.c(target),.d(io),.a(4),.b(6));if(q!==46||seq!==5||target!==46||io!==1166)$fatal(1,"unused defaults");
 q=f(,,);if(q!==67||seq!==7||target!==67||io!==1233)$fatal(1,"empty positions");
 q=identity({4'ha,4'h5});if(q!==165)$fatal(1,"single concatenation");
 q=identity(1?9:next());if(q!==9||seq!==7)$fatal(1,"conditional actual");
 q=classic(.b(2),.a(3));if(q!==5)$fatal(1,"classic named call");
 q=identity(.x());if(q!==8)$fatal(1,"named empty default");
 $display("TRACE binding complete");
end
endmodule
