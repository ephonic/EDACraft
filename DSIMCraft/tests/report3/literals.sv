`timescale 1ns/1ps
module top;
  logic [31:0] a;
  logic [15:0] b;
  string s;
  initial begin
 #1;
    a="AB"+1;b={"A",8'h42};s="AB";
    $display("TRACE mixed %h %h %0d %0d",a,b,("AB"==16'h4142),$bits("ABC"));
    s=b;$display("TRACE cast [%s]",s);
    $display("TRACE literal %h %h %h",("A"<<8),(1'bx ? "AB":"AC"),(1 ? "AB":16'h4321));
    $finish;
  end
endmodule
