`timescale 1ns/1ps
module top;
 logic[129:0] value=130'h2_0123456789abcdef_fedcba9876543210;
 logic[129:0] reversed,partial,large_slice;
 logic[143:0] padded;
 bit[129:0] binary;
 initial begin
  value[65:60]=6'bxz10zx;value[125:123]=3'bzx1;
  reversed={<<{value}};partial={<<17{value}};large_slice={<<65{value}};
  padded={<<byte{value}};binary={<<17{value}};
  #1;$display("TRACE wide %b %b %b %b %b %b",value,reversed,partial,large_slice,padded,binary);
  {<<17{partial}}=value;
  #1;$display("TRACE wide target %b",partial);
 end
endmodule
