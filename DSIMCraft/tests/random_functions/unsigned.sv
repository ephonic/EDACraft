`timescale 1ns/1ps
module top;
 integer seed=123,i;int unsigned first,next,again,value;logic[63:0] wide;
 integer seen_low=0,seen_high=0,seen_bit0=0,seen_bit1=0;
 initial begin
  first=$urandom(seed);next=$urandom;
  if(seed!=123)$fatal(1,"seed input modified");
  again=$urandom(123);if(again!==first)$fatal(1,"reseed");
  again=$urandom();if(again!==next)$fatal(1,"continued stream");
  wide=$urandom(123);if(wide[63:32]!==0||wide[31:0]!==first)$fatal(1,"unsigned width");
  for(i=0;i<512;i++)begin
   value=$urandom_range(2,5);if(value<2||value>5)$fatal(1,"reversed bounds");
   if(value==2)seen_low++;if(value==5)seen_high++;
   value=$urandom_range(1);if(value>1)$fatal(1,"default minimum");
   if(value==0)seen_bit0++;else seen_bit1++;
   value=$urandom_range(32'hffffffff,32'hfffffff0);
   if(value<32'hfffffff0)$fatal(1,"unsigned bounds");
   value=$urandom_range(0);if(value!==0)$fatal(1,"zero span");
   value=$urandom_range(7,7);if(value!==7)$fatal(1,"singleton");
   value=$urandom_range(32'hffffffff,0);
   if($isunknown(value))$fatal(1,"full range");
  end
  if(!seen_low||!seen_high||!seen_bit0||!seen_bit1)$fatal(1,"endpoints absent");
  $display("TRACE unsigned seed width ranges pass");
  #1;
 end
endmodule
