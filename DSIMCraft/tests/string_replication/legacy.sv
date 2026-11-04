module top;
 logic[7:0] packed_value;logic[31:0] chars;string result;int stage=0;
 initial begin
  packed_value={2{4'ha}};chars={2{"ab"}};result={2{4'ha}};
  $display("TRACE legacy %h %h %0d %0d %0d",packed_value,chars,result.len(),result.getc(0),$bits({2{"ab"}}));
  stage++;#1;$finish;
 end
endmodule
