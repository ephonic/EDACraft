`timescale 1ns/1ps
module top;
  string source="seed",observed;
  int wakes=0,length=0;
  function automatic string decorate(input string value);
    return {"<",value,">"};
  endfunction
  initial begin
    repeat(3)begin
      @(decorate(source));
      wakes++;observed=decorate(source);length=observed.len();
    end
  end
  initial begin
    #1;source="one";
    #1;source="two";
    #1;source="two"; // An equal string value must not trigger a change.
    #1;source="longer";
    #1;
    if(wakes!=3||observed!="<longer>"||length!=8)$fatal(1,"string function event dependencies");
    $display("TRACE events [%s] %0d %0d",observed,wakes,length);
    $finish;
  end
endmodule
