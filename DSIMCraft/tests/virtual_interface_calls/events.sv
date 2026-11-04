`timescale 1ns/1ps
interface bus_if;
 int state;
 function automatic bit enabled(input int value);return value>0;endfunction
endinterface
module top;
 bus_if a(),b();virtual bus_if vif;int edge_time,level_time;
 initial begin vif=a;
  fork
   begin @(posedge vif.enabled(vif.state));edge_time=$time;end
   begin wait(vif.enabled(vif.state));level_time=$time;end
   begin #1;vif=b;#1;a.state=1;#1;b.state=1;end
  join
  if(edge_time!=3||level_time!=3)$fatal(1,"event receiver binding");
  $display("TRACE vif events %0d %0d",edge_time,level_time);
 end
endmodule
