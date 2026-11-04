module top;
 int count=3,stage=0;string word="ab";logic[47:0] result;logic[15:0] short_value;
 function automatic int as_int(input string text);return text;endfunction
 function automatic void observe(input logic[31:0] value);$display("TRACE argument %h",value);endfunction
 initial begin
  result={count{"ab"}};short_value=word;
  $display("TRACE packed %h %h",result,short_value);
  result={count{word}};observe({count{word}});observe(word);
  $display("TRACE return %h",as_int(word));stage++;#1;$finish;
 end
endmodule
