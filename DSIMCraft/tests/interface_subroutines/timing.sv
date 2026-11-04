`timescale 10ns/1ps
interface timed_bus;
 integer state=0;
 task automatic pulse(input integer n,output integer snapshot);#1;state<=n;snapshot=state;#0;endtask
 function automatic integer now_value();return state;endfunction
 modport client(import pulse,now_value,input state);
endinterface
`timescale 1ns/1ps
module child(timed_bus.client p);
 integer snapshot;
 initial begin #2;p.pulse(9,snapshot);#1;
  if(snapshot!=0||p.now_value()!=9||$time!=13)$fatal(1,"FAIL lexical timescale/NBA");
  $display("TRACE timing %0t %0d %0d",$time,snapshot,p.state);end
endmodule
module top;timed_bus b();child c(b);initial begin #15;$finish;end endmodule
