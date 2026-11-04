`timescale 1ps/1ps
module top;
 string text;
 logic [15:0] word_value;
 int observed;
 function automatic string convert(input logic [15:0] value);return string'(value);endfunction
 initial begin
  word_value=16'h4142;text=convert(word_value);observed=text.len();
  #2;word_value=16'h4300;text=convert(word_value);observed=text.len();
  #1;word_value=16'h4445;text=convert(word_value);observed=text.getc(1);
  #2;if(text!="DE" || observed!=69)$fatal(1,"restored string conversion");
  $display("TRACE string rollback value=%s observed=%0d",text,observed);$finish;
 end
endmodule
