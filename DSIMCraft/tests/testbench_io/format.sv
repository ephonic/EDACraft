`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 string s,fmt="%s %0d %c %m";logic[23:0] p;int i=-3;
 initial begin
 s=$sformatf("literal %% %m %0d %h %b %c",i,12'haxz,4'bxz10,65);$display("TRACE FMT <%s>",s);
 s=$sformatf(fmt,"hello",i,16'h4241);$display("TRACE DYNAMIC <%s>",s);
 $sformat(s,"[%8s][%4d][%0d]","hi",i,130'h3ffffffffffffffffffffffffffffffff);$display("TRACE TASK <%s>",s);
 $sformat(p,"%s","abcdef");$display("TRACE PACK %h <%s>",p,p);
 #1;$timeformat(-9,2,"ns",0);s=$sformatf("%t",$time);$display("TRACE TIME <%s>",s);
 $finish;
 end
endmodule
