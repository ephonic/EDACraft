`timescale 1ps/1ps
module top;
  logic [7:0] q;
  initial begin
    q=1;#2;q=2;#3;$dumpvars(0,top);#1;q=3;
    #2;$display("TRACE late complete");$finish;
  end
endmodule
