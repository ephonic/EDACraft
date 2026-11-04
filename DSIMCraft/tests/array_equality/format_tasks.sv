module top;
 int calls=0;
 string text,fmt="%s %0d %h";
 function automatic int next();calls++;return calls;endfunction
 function automatic string make();
  string result;
  $swrite(result,"lhs=%0d rhs=%0d",next(),next());
  return result;
 endfunction
 function automatic string make_format();
  string result;
  $sformat(result,"value=%0d",next());
  return result;
 endfunction
 reg [127:0] packed_text;
 initial begin
  text=make();$display("TRACE swrite %s calls=%0d",text,calls);
  $display("TRACE sformat %s",make_format());
  $swrite(text,fmt,"data",-5,8'haz);$display("TRACE dynamic %s",text);
  $swrite(packed_text,"msg %0d",25);$display("TRACE packed %s",packed_text);
 end
endmodule
