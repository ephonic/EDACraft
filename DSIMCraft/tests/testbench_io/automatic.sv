`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 string first,second;int done=0;int number=5;
 task automatic load(input string label,input int ticks,output string answer,ref int n);
  string value="fallback";string fmt="text=%s";int ok;
  ok=$value$plusargs(fmt,value);
  #ticks;
  n++;
  answer=$sformatf("%m %s/%s/%0d/%0d",label,value,n,ok);
 endtask
 function automatic string tag(input int n);
  return $sformatf("%m:%0d",n);
 endfunction
 initial begin #1;load("one",1,first,number);done++;end
 initial begin #2;load("two",2,second,number);done++;end
 initial begin
  #5;
  $display("TRACE AUTO <%s> <%s> %0d %0d <%s>",first,second,number,done,tag(9));
  $finish;
 end
 final $display("TRACE FINAL <%s>",$sformatf("%m:%0d:%0d",number,$test$plusargs("mode")));
endmodule
