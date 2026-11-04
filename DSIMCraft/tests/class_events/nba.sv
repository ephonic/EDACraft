`timescale 1ps/1ps
module top;
 class C;event pulse;task notify();->>pulse;endtask endclass
 C a,b,selected;int hits=0,other=0,delays=0,stage=0;
 function automatic int ticks();delays++;return 2;endfunction
 initial begin
  a=new;b=new;selected=a;
  fork
   begin @(a.pulse);hits++;stage=1;@(a.pulse);hits++;end
   begin @(b.pulse);other++;end
   begin
    a.notify();if(hits!=0)$fatal(1,"NBA ran in Active");
    #1;if(stage!=1)$fatal(1,"NBA wake");
    ->> #(ticks()) selected.pulse;selected=b;
    #3;if(hits!=2||other!=0||delays!=1)$fatal(1,"delayed event receiver capture");
   end
  join_any
  #5;
  if(hits!=2||other!=0||delays!=1)$fatal(1,"NBA event identity");
  $display("TRACE class nba %0d %0d %0d",hits,other,delays);$finish;
 end
endmodule
