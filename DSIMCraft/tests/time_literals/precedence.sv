timeunit 10ns/1ns;
module before_directive;
 initial begin if(10ns!=1)$fatal(1,"CU unit");end
endmodule
`timescale 1ns/1ps
module after_directive;
 timeprecision 10ps;
 initial begin if(10ns!=10)$fatal(1,"directive unit");end
endmodule
`resetall
module reset_scope;
 initial begin if(10ns!=1)$fatal(1,"reset CU");end
endmodule
module top;
 timeunit 1.0ns/0.1ns;
 timeprecision 100ps;
 int observed=0;
 timeunit 1000ps;
 before_directive a();after_directive b();reset_scope c();
 initial begin #1.25ns;observed=1;if($realtime!=1.3)$fatal(1,"local unit");$display("TRACE precedence");$finish;end
endmodule
