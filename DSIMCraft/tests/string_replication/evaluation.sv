module top;
 int count=2,calls=0,stage=0;string result;
 function automatic string value();calls++;return "ab";endfunction
 function automatic int amount(input int n);return n+1;endfunction
 initial begin
  result={count{value()}};$display("TRACE evaluation %0d %s",calls,result);
  count=0;result={count{value()}};$display("TRACE zero evaluation %0d %0d",calls,result.len());
  count=-1;result={count{value()}};$display("TRACE negative evaluation %0d %0d",calls,result.len());
  count=2;result={amount(count){"x"}};$display("TRACE count function %s",result);
  stage++;#1;$finish;
 end
endmodule
