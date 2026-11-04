module unused;
 timeunit 1ns/1ps;
endmodule
module top;
 timeunit 1ns/100ps;
 realtime delay=1.25ns;
 class delay_box;
  realtime delay=1.25ns;
 endclass
 delay_box box;
 int observed=0;
 initial begin
  box=new();
  #(box.delay);observed=1;
  if($realtime!=1.3)$fatal(1,"runtime precision");
  #1.25ns;observed=2;
  if($realtime!=2.6)$fatal(1,"literal precision");
  #(delay+250ps);observed=3;
  if($realtime!=4.1)$fatal(1,"expression precision");
  observed<=#250ps 4;#500ps;
  if(observed!=4||$realtime!=4.6)$fatal(1,"delayed NBA");
  $display("TRACE rounding %0.17g %0d",$realtime,observed);$finish;
 end
endmodule
