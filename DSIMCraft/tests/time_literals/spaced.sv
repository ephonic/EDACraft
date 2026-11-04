module top;
 timeunit 1 ns / 100 ps;
 timeprecision 100 ps;
 int observed=0;
 initial begin #1.25ns;observed=1;if($realtime!=1.3)$fatal(1,"spaced declaration");$display("TRACE spaced %0.17g",$realtime);$finish;end
endmodule
