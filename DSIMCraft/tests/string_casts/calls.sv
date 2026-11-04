package types;
 typedef string text_t;
 function automatic text_t wrap(input byte c,input string prefix=text_t'(8'h41));return {prefix,text_t'(c)};endfunction
endpackage
module top;
 import types::*;
 class Printer;
  byte separator;
  function new();separator=8'h3a;endfunction
  virtual function string format_word(input int value);
   return {string'(value),string'(separator),"done"};
  endfunction
 endclass
 Printer printer;
 text_t result;
 int observed;
 initial begin
  printer=new();result=printer.format_word(32'h4142);
  if(result!="AB:done")$fatal(1,"class cast/return");
  result=wrap(8'h42);if(result!="AB")$fatal(1,"named string alias/default/call");
  result=text_t'(24'h636162);if(result.toupper()!="CAB")$fatal(1,"alias cast method");
  observed=result.len();if(observed!=3)$fatal(1,"numeric string observation");
  $display("TRACE string calls value=%s",result);$finish;
 end
endmodule
