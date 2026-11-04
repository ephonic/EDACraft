interface bus_if;
 timeunit 100ps;timeprecision 1ps;
 task automatic pause(output real local_time);#3;local_time=$realtime;endtask
endinterface
module top;
 timeunit 1ns;timeprecision 1ps;
 bus_if a();virtual bus_if vif;real local_time,caller_time;
 initial begin vif=a;vif.pause(local_time);caller_time=$realtime;
  if(local_time!=3.0||caller_time<0.2999||caller_time>0.3001)$fatal(1,"timescope");
  $display("TRACE vif timing %0.2f %0.2f",local_time,caller_time);
 end
endmodule
