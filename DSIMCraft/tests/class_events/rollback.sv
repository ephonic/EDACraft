`timescale 1ps/1ps
module top;
 class C;event pulse;endclass
 C source,ghost;int observed=0,hits=0;
 initial begin
  source=new;
  fork
   begin @(source.pulse);hits++;observed=9;@(source.pulse);hits++;observed=7;end
   begin #2;ghost=new;->ghost.pulse;->source.pulse;#1;ghost=new;->ghost.pulse;->source.pulse;end
  join
  #2;if(hits!=2||observed!=7)$fatal(1,"event replay");
  $display("TRACE class rollback %0d %0d",hits,observed);$finish;
 end
endmodule
