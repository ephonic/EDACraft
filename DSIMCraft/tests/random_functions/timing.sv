`timescale 1ns/1ps
module top;
 integer seed=1,i=0;logic[31:0] q=0,expected;int unsigned discard,delayed,nb;
 initial begin
  discard=$urandom(98);expected=$urandom_range(9,9);
  for(i=0;i<4;i++)begin
   q<=#2 $random(seed);
   delayed = #1 $urandom_range(9,9);
   nb<=#1 $urandom_range(6,6);
   #2;
   if(delayed!==9||nb!==6||$isunknown(q))$fatal(1,"delayed random assignment");
  end
  if(q!==32'hae130c5c)$fatal(1,"legacy delayed sequence");
  $display("TRACE random delay NBA replay pass");
 end
endmodule
