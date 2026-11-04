`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 logic[129:0] wide=0;logic[15:0] packed_value=0;logic[7:0] a,b;
 string s,fmt="[%s:%0d]";int r,idx=8;int errors=0;
 initial begin
  r=$value$plusargs("hex=%h",wide[73+:48]);
  $display("TRACE SLICE %0d %h",r,wide);
  r=$value$plusargs("pair=%h",{a,b});
  $display("TRACE CONCAT %0d %h %h",r,a,b);
  $sformat(packed_value,fmt,"abc",-1);
  $sformat(s,fmt,"abc",-1);
  $display("TRACE WRITE %h <%s>",packed_value,s);
  void'($value$plusargs("n=%d",idx));
  $test$plusargs("discard");
  void'($sformatf("ignored:%0d",idx));
  #1;r=$value$plusargs("oct=%o",wide);
  $display("TRACE OCTAL %0d %h",r,wide);
  #1;r=$value$plusargs("bin=%b",wide);
  $display("TRACE BINARY %0d %h",r,wide);
  $finish;
 end
endmodule
