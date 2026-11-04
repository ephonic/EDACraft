module top;
 logic[95:0] count=2;logic signed[95:0] negative=-1;logic[95:0] unknown=96'hx00000002;
 byte unsigned maximum=255;string word="xy",result;logic[79:0] packed_value;int stage=0;
 initial begin
  result={count{word}};packed_value=result;$display("TRACE wide %0d %h",result.len(),packed_value);
  result={negative{word}};$display("TRACE wide negative %0d",result.len());
  result={unknown{word}};$display("TRACE wide unknown %0d",result.len());
  result={maximum{"a"}};$display("TRACE unsigned %0d %0d",result.len(),result.getc(254));
  word="";count=96'h100000000;result={count{word}};$display("TRACE empty %0d",result.len());
  stage++;#1;$finish;
 end
endmodule
