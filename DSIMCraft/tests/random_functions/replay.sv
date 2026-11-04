`timescale 1ns/1ps
module top;
 logic[31:0] unsigned_samples[4],legacy_samples[4];
 int unsigned discarded,value;integer i=0;
 initial begin
  discarded=$urandom(2718);
  for(i=0;i<4;i++)begin
   #1;unsigned_samples[i]=$urandom();legacy_samples[i]=$random;
  end
  if(legacy_samples[0]!==32'h12153524||legacy_samples[1]!==32'hc0895e81||legacy_samples[2]!==32'h8484d609||legacy_samples[3]!==32'hb1f05663)$fatal(1,"global legacy state");
  discarded=$urandom(2718);
  for(i=0;i<4;i++)begin value=$urandom;if(value!==unsigned_samples[i])$fatal(1,"persistent unsigned state");end
  $display("TRACE random global and process state replay pass");
 end
endmodule
