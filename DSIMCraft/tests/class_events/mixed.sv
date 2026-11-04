`timescale 1ps/1ps
module child;event pulse;endmodule
module top;
 class C;event pulse;endclass
 child u();C a,b,selected;bit clock=0,enabled=0;int mixed=0,guarded=0,hierarchy=0,query=0;
 initial begin
  a=new;b=new;selected=a;
  fork
   begin @(selected.pulse or posedge clock);mixed++;@(b.pulse or posedge clock);mixed++;end
   begin @(a.pulse iff enabled);guarded++;end
   begin @(u.pulse);hierarchy++;wait(u.pulse.triggered);query++;end
   begin
    #1;selected=b;->b.pulse;#1;if(mixed!=0)$fatal(1,"mixed wait changed receiver");
    ->a.pulse;#1;enabled=1;->a.pulse;clock=1;->u.pulse;
   end
  join
  if(mixed!=2||guarded!=1||hierarchy!=1||query!=1)$fatal(1,"mixed or hierarchical events");
  $display("TRACE class mixed %0d %0d %0d %0d",mixed,guarded,hierarchy,query);$finish;
 end
 initial begin #100;$fatal(1,"mixed wait lost");end
endmodule
