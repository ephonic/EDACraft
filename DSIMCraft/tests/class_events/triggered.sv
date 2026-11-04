`timescale 1ps/1ps
module top;
 class C;event pulse;int enabled=0;endclass
 C c;int changes=0,rises=0,falls=0,guarded=0,late=0,level=0,early=0;
 initial begin
  c=new;
  fork
   begin @(c.pulse.triggered);changes++;end
   begin @(posedge c.pulse.triggered);rises++;end
   begin @(negedge c.pulse.triggered);falls++;end
   begin @(c.pulse iff c.enabled);guarded++;end
   begin wait(c.pulse.triggered);early++;end
   begin
    #1;->c.pulse;
    if(!c.pulse.triggered)$fatal(1,"persistent trigger");
    wait(c.pulse.triggered);level++;
    fork begin @(c.pulse.triggered);late++;end join_none
    #1;
    if(c.pulse.triggered||guarded!=0)$fatal(1,"timestamp or iff");
    c.enabled=1;#1;->c.pulse;#1;
   end
  join_any
  // Let all independently armed controls settle; the falling/late observers
  // intentionally remain blocked because implicit time advance is no edge.
  #4;
  if(changes!=1||rises!=1||falls!=0||guarded!=1||late!=0||level!=1||early!=1)$fatal(1,"query semantics");
  $display("TRACE class triggered %0d %0d %0d %0d %0d %0d",changes,rises,falls,guarded,late,level);$finish;
 end
endmodule
