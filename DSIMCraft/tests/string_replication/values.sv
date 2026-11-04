module top;
 int count=3;logic[3:0] uncertain=4'bxx01;string word="ab",result;int stage=0;
 initial begin
  result={count{"ab"}};$display("TRACE literal %0d %s",result.len(),result);
  $display("TRACE direct %s",{count{"ab"}});
  result={count{word}};$display("TRACE value %s",result);
  count=0;result={count{word}};$display("TRACE zero %0d",result.len());
  count=-1;result={count{word}};$display("TRACE negative %0d",result.len());
  result={uncertain{word}};$display("TRACE unknown %0d",result.len());
  stage++;#1;$finish;
 end
endmodule
