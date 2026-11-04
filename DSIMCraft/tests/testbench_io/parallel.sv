`timescale 1ns/1ps
module lane(output integer result);
 string text,fmt="%0d";int count=0,errors=0,base=10,ok;
 initial begin
  ok=$value$plusargs("base=%d",base);
  repeat(4) begin
   #0.5;count++;
   text=$sformatf(fmt,base+count);
   result=text.atoi();
   if(result!=base+count||!ok||!$test$plusargs("mode"))errors++;
  end
 end
endmodule
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 wire[31:0] first,second;
 lane u(first);lane v(second);
 initial begin #3;$finish;end
endmodule
