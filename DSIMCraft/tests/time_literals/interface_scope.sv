interface bus;
 timeunit 10ns/100ps;
 logic observed=0;
 task automatic drive(input realtime d=250ps);#d;observed=1;endtask
endinterface
module top;
 timeunit 1ns/1ps;
 bus b();
 initial begin b.drive();if($realtime!=0.3||b.observed!=1)$fatal(1,"interface delay");$display("TRACE interface %0.17g",$realtime);$finish;end
endmodule
