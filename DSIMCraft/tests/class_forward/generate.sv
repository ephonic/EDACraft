`timescale 1ps/1ps
module top;
 genvar i;
 for(i=0;i<2;i++) begin: lanes
  typedef class Word;
  typedef Word Alias;
  class Word;
   logic[i+64:0] bits='1;
  endclass
  Alias value=new;
  logic[i+64:0] observed;
  initial begin
   observed=value.bits;
   #(i+1);$display("TRACE generate %0d %h",i,observed);
  end
 end
endmodule
