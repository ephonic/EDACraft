`timescale 1ns/1ps
module top;
  string text="abcd";int changes=0,observed=0;
  always @(text) begin changes++;observed=text.getc(0);end
  initial begin
    #1;text.putc(64'h100000001,16'h5141);
    #1;text.itoa(12);
    #1;text.hextoa(123);
    #1;
    $display("TRACE boundaries %s %0d %0d",text,changes,observed);$finish;
  end
endmodule
