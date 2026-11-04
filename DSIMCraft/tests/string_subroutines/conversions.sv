`timescale 1ns/1ps
module top;
  typedef string text_t;
  string fallback="base",result;
  int calls=0;
  function automatic string identity(input string value=fallback);
    calls++;return value;
  endfunction
  function automatic text_t from_word(input logic[23:0] value);
    return value;
  endfunction
  // Classic declarations use the same typed storage and copy rules.
  task copy_classic;
    input string source;
    output text_t destination;
    begin destination={source,"/classic"};end
  endtask
  initial begin
    #1;
    result=identity(16'h4142);if(result!="AB")$fatal(1,"integral input to string formal");
    result=from_word(24'h414243);if(result!="ABC")$fatal(1,"integral string return conversion");
    result=identity();if(result!="base")$fatal(1,"default string argument");
    fallback="changed";result=identity(.value());
    if(result!="changed")$fatal(1,"default must be evaluated at each call");
    copy_classic(identity("tail"),result);
    if(result!="tail/classic"||calls!=4)$fatal(1,"classic string declarations/call count");
    $display("TRACE conversions [%s] %0d",result,calls);
    #1;$finish;
  end
endmodule
