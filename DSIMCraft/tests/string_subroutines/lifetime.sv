`timescale 1ns/1ps
module top;
  string result;
  int score=0;
  function string remember(input string value,input bit update);
    if(update)remember=value;
  endfunction
  function automatic string fresh(input string value,input bit update);
    if(update)fresh=value;
  endfunction
  function automatic string repeat_text(input string value,input int count);
    if(count<=0)return "";
    return {value,repeat_text(value,count-1)};
  endfunction
  initial begin
    #1;
    result=remember("kept",1);if(result!="kept")$fatal(1,"static string result");
    result=remember("ignored",0);if(result!="kept")$fatal(1,"persistent static string result");
    result=fresh("once",1);if(result!="once")$fatal(1,"automatic string result");
    result=fresh("ignored",0);if(result!="")$fatal(1,"automatic result must be reset");
    result=repeat_text("xy",4);score=result.len();
    if(result!="xyxyxyxy"||score!=8)$fatal(1,"recursive string argument/result frames");
    $display("TRACE lifetime [%s] %0d",result,score);
    #1;$finish;
  end
endmodule
