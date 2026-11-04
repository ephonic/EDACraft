`timescale 1ns/1ps
module top;
  typedef string text_t;
  text_t original, result, output_text, inout_text;
  integer score=0;
  function automatic text_t wrap(input text_t value="default", input string suffix="!");
    return {"[",value,suffix,"]"};
  endfunction
  function automatic string via_name(input string value);
    via_name=wrap(.suffix("?"),.value(value));
  endfunction
  function automatic int edit(input string value, output string copy, inout text_t accum);
    if(copy!="")return -1000;
    copy=wrap(value);accum={accum,value};return copy.len()+accum.len();
  endfunction
  task automatic transfer(input text_t value="task",output string copy,inout string accum);
    copy=via_name(value);accum={accum,"/",value};
  endtask
  initial begin
    #1;
    if(original!="")$fatal(1,"string default value");
    original="alpha";inout_text="pre";output_text="old";
    result=wrap();if(result!="[default!]")$fatal(1,"string default arguments");
    result=via_name(original);if(result!="[alpha?]")$fatal(1,"nested string return");
    score=edit(original,output_text,inout_text);
    if(output_text!="[alpha!]"||inout_text!="prealpha"||score!=16)$fatal(1,"function string copy in/out");
    transfer(.copy(output_text),.accum(inout_text));
    if(output_text!="[task?]"||inout_text!="prealpha/task")$fatal(1,"task named/default string arguments");
    // Return values can immediately become string method receivers.
    score=via_name("beta").len();
    if(score!=7)$fatal(1,"method on string function result");
    result=wrap(via_name("x"),"+");
    if(result!="[[x?]+]")$fatal(1,"nested string actual");
    $display("TRACE signatures [%s] [%s] [%s] %0d",result,output_text,inout_text,score);
    #1;$finish;
  end
endmodule
