module top;
 string s;string q[$];int stage=0;
 function automatic int bits_of(input string value);return $bits(value);endfunction
 function automatic int queue_count(input string values[$]);return $size(values);endfunction
 initial begin
  $display("TRACE empty %0d",bits_of(s));s="abc";q='{"A","B","C"};stage++;#1;
  $display("TRACE queries %0d %0d",bits_of(s),queue_count(q));$finish;
 end
endmodule
