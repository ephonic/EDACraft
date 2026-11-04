`timescale 1ns/1ps
module top;
 integer effect=0,result=0;
 function automatic integer work(input integer count);
  integer i;
  begin
   for(i=0;i<count;i=i+1)effect=effect+1;
   return effect;
  end
 endfunction
 initial begin
  result=work(16);
  if(effect!=16||result!=16)$fatal(1,"function side effects repeated");
  $display("TRACE function boundary %0d %0d",effect,result);
 end
endmodule
