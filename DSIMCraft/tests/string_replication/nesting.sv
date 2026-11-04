module top;
 int a=2,b=3,stage=0;bit choose=1;logic[7:0] byte_value=8'h41;string word="b",result;
 initial begin
  result={"[",{a{{b{"xy"}}}},"]"};$display("TRACE nested %s",result);
  result=choose?{a{"xy"}}:"no";$display("TRACE conditional %s",result);
  result={a{byte_value,word}};$display("TRACE mixed %s",result);
  result={a{8'h41}};$display("TRACE numeric %s",result);
  stage++;#1;$finish;
 end
endmodule
