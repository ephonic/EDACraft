class Recorder;
 string value;int count=0;
 function string record(input int number);count++;$swrite(value,"[",number,"]/%0d",count);return value;endfunction
 function string bits(input byte unsigned number);$swriteh(value,number);return value;endfunction
endclass
module top;
 Recorder recorder;string s;int calls=0,stage=0;
 function automatic int next_value();calls++;return calls;endfunction
 function automatic string rendered();string local_text;$swrite(local_text,next_value(),"/",next_value());return local_text;endfunction
 initial begin
  recorder=new();s=recorder.record(17);$display("TRACE record <%s>",s);
  s=rendered();$display("TRACE effects <%s> %0d",s,calls);
  s=recorder.bits(8'haf);$display("TRACE radix <%s> %0d",s,recorder.count);
  stage++;#1;s=recorder.record(-9);$display("TRACE again <%s>",s);$finish;
 end
endmodule
