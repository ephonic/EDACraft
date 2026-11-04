`timescale 1ns/1ps
module top;integer a=0,b=0,k=0;
function automatic integer f(input integer n);
 begin : search
  f=7;
  for(integer j=0;j<4;j++)begin
   if(j==n)disable search;
   f=f+1;
  end
  f=99;
 end
endfunction
initial begin
 begin : scan
  for(k=0;k<5;k++)begin
   if(k==3)disable scan;
   a=a+k;
  end
  a=99;
 end
 b=f(2);#1;$display("TRACE lexical %0d %0d %0d",a,b,k);$finish;
end
endmodule
