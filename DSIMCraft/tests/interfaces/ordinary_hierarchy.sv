`timescale 1ps/1ps
module leaf;
 logic[7:0] value=0;
endmodule
module top;
 leaf x();int observed;
 initial begin
  #1;x.value=7;#1;observed=x.value;$display("TRACE ordinary %0d",observed);
  #1;x.value[3:0]=9;#1;observed=x.value;$display("TRACE ordinary %0d",observed);
 end
endmodule
