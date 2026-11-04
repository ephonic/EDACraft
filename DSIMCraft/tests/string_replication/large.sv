module top;
 int count=4096,stage=0;string word="abcdefgh",result;
 initial begin
  result={count{word}};
  $display("TRACE large %0d %s %s",result.len(),result.substr(0,7),result.substr(32760,32767));
  stage++;#1;$finish;
 end
endmodule
