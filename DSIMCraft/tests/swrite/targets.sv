module top;
 string values[$]='{"",""};string s="old";logic[23:0] packed_value;logic[127:0] wide;int stage=0,index=0;
 initial begin
  $swrite(packed_value,"abcdef");$display("TRACE packed <%s> %h",packed_value,packed_value);
  $swrite(wide,"ABC",8'd7);$display("TRACE wide <%s> %h",wide,wide);
  $swrite(values[index],"%0d",17);$display("TRACE indexed <%s> %0d",values[0],index);
  $swrite(s,s,"/",8'd3);$display("TRACE self <%s>",s);
  stage++;#1;$swrite(s,{"AB","CD"});$display("TRACE concat <%s>",s);$finish;
 end
endmodule
