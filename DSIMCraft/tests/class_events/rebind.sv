`timescale 1ps/1ps
module top;
 class C;event pulse;endclass
 C a,b,selected;int hits=0,calls=0,level=0;
 function automatic C receiver();calls++;return selected;endfunction
 initial begin
  a=new;b=new;selected=a;
  fork
   begin @(receiver().pulse);hits++;end
   begin #1;selected=b;->b.pulse;#1;
    if(hits!=0||calls!=1)$fatal(1,"wait operand rebound or reevaluated");
    ->a.pulse;
   end
  join
  fork
   begin wait(selected.pulse.triggered);level++;end
   begin #1;->a.pulse;#1;if(level!=0)$fatal(1,"level wait followed old receiver");->b.pulse;end
  join
  fork
   begin repeat(32)begin @(selected.pulse);hits++;end end
   begin repeat(32)begin #1;->b.pulse;end end
  join
  if(hits!=33||calls!=1||level!=1)$fatal(1,"subscription reuse");
  $display("TRACE class rebind %0d %0d",hits,calls);$finish;
 end
 initial begin #100;$fatal(1,"lost event");end
endmodule
